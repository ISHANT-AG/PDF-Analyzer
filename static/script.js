/**
 * Multi-PDF Topic Extractor - Frontend Logic & Interactivity
 * Handles drag-and-drop file management, asynchronous API requests,
 * dynamic side-by-side comparison rendering, and report exports.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const btnBrowse = document.getElementById('btnBrowse');
    const selectedFilesContainer = document.getElementById('selectedFilesContainer');
    const filesGrid = document.getElementById('filesGrid');
    const fileCountBadge = document.getElementById('fileCountBadge');
    const btnClearFiles = document.getElementById('btnClearFiles');

    const extractorForm = document.getElementById('extractorForm');
    const topicInput = document.getElementById('topicInput');
    const btnClearInput = document.getElementById('btnClearInput');
    const btnSubmit = document.getElementById('btnSubmit');
    const btnText = btnSubmit.querySelector('.btn-text');
    const btnLoading = btnSubmit.querySelector('.btn-loading');

    const loadingCard = document.getElementById('loadingCard');
    const alertBox = document.getElementById('alertBox');
    const alertMessage = document.getElementById('alertMessage');
    const btnAlertClose = document.getElementById('btnAlertClose');

    const resultsSection = document.getElementById('resultsSection');
    const resultsContainer = document.getElementById('resultsContainer');
    const resTopicDisplay = document.getElementById('resTopicDisplay');
    const resTotalPdfs = document.getElementById('resTotalPdfs');
    const resTotalMatches = document.getElementById('resTotalMatches');

    const btnModeSideBySide = document.getElementById('btnModeSideBySide');
    const btnModeGrid = document.getElementById('btnModeGrid');
    const btnCopyReport = document.getElementById('btnCopyReport');
    const btnDownloadReport = document.getElementById('btnDownloadReport');

    const btnToggleExplainer = document.getElementById('btnToggleExplainer');
    const explainerContent = document.getElementById('explainerContent');
    const explainerChevron = document.getElementById('explainerChevron');

    // --- State Management ---
    let selectedFiles = []; // Array of File objects
    let currentResultsData = null; // Stores last successful API response
    const MAX_FILES = 5;

    // =========================================================================
    // 1. File Upload & Drag-and-Drop Management
    // =========================================================================

    btnBrowse.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('drag-over');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const droppedFiles = Array.from(e.dataTransfer.files);
        handleNewFiles(droppedFiles);
    });

    fileInput.addEventListener('change', (e) => {
        const pickedFiles = Array.from(e.target.files);
        handleNewFiles(pickedFiles);
        // Reset file input value so selecting the same file triggers change again
        fileInput.value = '';
    });

    function handleNewFiles(newFiles) {
        hideAlert();
        const validPdfFiles = newFiles.filter(f => f.name.toLowerCase().endsWith('.pdf'));

        if (validPdfFiles.length < newFiles.length) {
            showAlert('Some non-PDF files were ignored. Only .pdf files are supported.', 'warning');
        }

        if (validPdfFiles.length === 0) return;

        // Check for duplicates
        for (const file of validPdfFiles) {
            const isDuplicate = selectedFiles.some(
                existing => existing.name === file.name && existing.size === file.size
            );

            if (!isDuplicate) {
                if (selectedFiles.length >= MAX_FILES) {
                    showAlert(`Maximum limit of ${MAX_FILES} PDFs reached. Extra files were not added.`, 'warning');
                    break;
                }
                selectedFiles.push(file);
            }
        }

        renderSelectedFiles();
    }

    function renderSelectedFiles() {
        filesGrid.innerHTML = '';
        fileCountBadge.textContent = selectedFiles.length;

        if (selectedFiles.length === 0) {
            selectedFilesContainer.style.display = 'none';
            return;
        }

        selectedFilesContainer.style.display = 'block';

        selectedFiles.forEach((file, index) => {
            const pill = document.createElement('div');
            pill.className = 'file-item-pill';
            pill.innerHTML = `
                <div class="file-item-info">
                    <svg class="file-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <div>
                        <div class="file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
                        <div class="file-size">${formatBytes(file.size)}</div>
                    </div>
                </div>
                <button type="button" class="btn-remove-file" data-index="${index}" title="Remove file">&times;</button>
            `;
            filesGrid.appendChild(pill);
        });

        // Attach remove button listeners
        filesGrid.querySelectorAll('.btn-remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.target.getAttribute('data-index'), 10);
                selectedFiles.splice(idx, 1);
                renderSelectedFiles();
            });
        });
    }

    btnClearFiles.addEventListener('click', () => {
        selectedFiles = [];
        renderSelectedFiles();
    });

    // =========================================================================
    // 2. Topic Input & Preset Suggestion Chips
    // =========================================================================

    topicInput.addEventListener('input', () => {
        btnClearInput.style.display = topicInput.value.trim() ? 'block' : 'none';
    });

    btnClearInput.addEventListener('click', () => {
        topicInput.value = '';
        btnClearInput.style.display = 'none';
        topicInput.focus();
    });

    document.querySelectorAll('.suggestion-chips .chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const topic = chip.getAttribute('data-topic');
            topicInput.value = topic;
            btnClearInput.style.display = 'block';
            topicInput.focus();
        });
    });

    // =========================================================================
    // 3. Form Submission & Extraction Request
    // =========================================================================

    extractorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideAlert();

        const topic = topicInput.value.trim();
        if (!topic) {
            showAlert('Please enter a topic or keyword to search.', 'warning');
            topicInput.focus();
            return;
        }

        if (selectedFiles.length === 0) {
            showAlert('Please select or drop at least 1 PDF file to analyze.', 'warning');
            return;
        }

        // Prepare FormData
        const formData = new FormData();
        formData.append('topic', topic);
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        // Set Loading State
        setLoadingState(true);

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Extraction failed. Please try again.');
            }

            // Save state & render
            currentResultsData = data;
            renderResults(data);

            // Smooth scroll to results
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (err) {
            console.error('Extraction error:', err);
            showAlert(err.message || 'An error occurred while analyzing the PDFs.', 'error');
        } finally {
            setLoadingState(false);
        }
    });

    function setLoadingState(isLoading) {
        if (isLoading) {
            btnSubmit.disabled = true;
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline-flex';
            loadingCard.style.display = 'flex';
            resultsSection.style.display = 'none';
        } else {
            btnSubmit.disabled = false;
            btnText.style.display = 'inline-flex';
            btnLoading.style.display = 'none';
            loadingCard.style.display = 'none';
        }
    }

    // =========================================================================
    // 4. Results Rendering (Side-by-Side & Grid)
    // =========================================================================

    function renderResults(data) {
        resTopicDisplay.textContent = `"${data.topic}"`;
        resTotalPdfs.textContent = data.total_files_analyzed;
        resTotalMatches.textContent = data.total_matches_found;

        resultsContainer.innerHTML = '';

        data.results.forEach((doc) => {
            const docCard = document.createElement('div');
            docCard.className = 'doc-card';

            const statusClass = doc.found ? 'found' : 'empty';
            const statusLabel = doc.found ? `${doc.matches.length} Matched` : 'No Match';

            let matchesContentHtml = '';

            if (doc.found && doc.matches.length > 0) {
                matchesContentHtml = doc.matches.map(m => {
                    const isSemantic = m.match_type.includes('TF-IDF');
                    const badgeClass = isSemantic ? 'semantic' : 'keyword';
                    const scoreText = isSemantic ? `Relevance: ${m.score_percentage}%` : 'Keyword Match';

                    return `
                        <div class="match-item">
                            <div class="match-meta-bar">
                                <div class="match-meta-left">
                                    <span class="rank-badge">#${m.rank}</span>
                                    <span class="page-badge">Page ${m.page}</span>
                                </div>
                                <div class="match-meta-right">
                                    <span class="score-badge ${badgeClass}">${scoreText}</span>
                                    <button type="button" class="btn-copy-snippet" data-text="${escapeAttribute(m.raw_text)}" title="Copy this paragraph">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                            <div class="match-text">${m.highlighted_html}</div>
                        </div>
                    `;
                }).join('');
            } else {
                matchesContentHtml = `
                    <div class="doc-empty-state">
                        <div class="empty-icon">🔍</div>
                        <div class="empty-text">No relevant content found for <strong>"${escapeHtml(data.topic)}"</strong> in this document.</div>
                    </div>
                `;
            }

            docCard.innerHTML = `
                <div class="doc-header">
                    <div class="doc-info">
                        <div class="doc-title-row">
                            <svg class="doc-pdf-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            <span class="doc-filename" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
                        </div>
                        <span class="doc-submeta">${doc.total_pages} Pages &bull; ${doc.total_paragraphs} Paragraphs Analyzed</span>
                    </div>
                    <span class="doc-status-badge ${statusClass}">${statusLabel}</span>
                </div>
                <div class="doc-matches-list">
                    ${matchesContentHtml}
                </div>
            `;

            resultsContainer.appendChild(docCard);
        });

        // Attach snippet copy handlers
        resultsContainer.querySelectorAll('.btn-copy-snippet').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const textToCopy = btn.getAttribute('data-text');
                copyToClipboard(textToCopy, btn);
            });
        });

        resultsSection.style.display = 'flex';
    }

    // =========================================================================
    // 5. View Mode Switching (Side-by-Side vs Grid)
    // =========================================================================

    btnModeSideBySide.addEventListener('click', () => {
        btnModeSideBySide.classList.add('active');
        btnModeGrid.classList.remove('active');
        resultsContainer.className = 'results-container mode-side-by-side';
    });

    btnModeGrid.addEventListener('click', () => {
        btnModeGrid.classList.add('active');
        btnModeSideBySide.classList.remove('active');
        resultsContainer.className = 'results-container mode-grid';
    });

    // =========================================================================
    // 6. Export & Copy Actions
    // =========================================================================

    btnCopyReport.addEventListener('click', () => {
        if (!currentResultsData) return;
        const textReport = generatePlainTextReport(currentResultsData);
        copyToClipboard(textReport, btnCopyReport, 'Copied All!');
    });

    btnDownloadReport.addEventListener('click', () => {
        if (!currentResultsData) return;
        const textReport = generatePlainTextReport(currentResultsData);
        downloadTextFile(`Topic_Extraction_${currentResultsData.topic.replace(/\s+/g, '_')}.txt`, textReport);
    });

    function generatePlainTextReport(data) {
        let lines = [];
        lines.push('================================================================');
        lines.push(' MULTI-PDF TOPIC EXTRACTOR - COMPARISON REPORT');
        lines.push('================================================================');
        lines.push(`Topic / Keyword: "${data.topic}"`);
        lines.push(`Date: ${new Date().toLocaleString()}`);
        lines.push(`Total PDFs Analyzed: ${data.total_files_analyzed}`);
        lines.push(`Total Matches Found: ${data.total_matches_found}`);
        lines.push('================================================================\n');

        data.results.forEach((doc, idx) => {
            lines.push(`SOURCE [${idx + 1}]: ${doc.filename} (${doc.total_pages} pages, ${doc.total_paragraphs} paragraphs)`);
            lines.push('----------------------------------------------------------------');

            if (!doc.found || doc.matches.length === 0) {
                lines.push('  No relevant paragraphs found for this topic.\n');
            } else {
                doc.matches.forEach(m => {
                    lines.push(`  * Rank #${m.rank} | Page ${m.page} | ${m.match_type} (Score: ${m.score})`);
                    lines.push(`    "${m.raw_text}"\n`);
                });
            }
        });

        lines.push('================================================================');
        lines.push(' End of Report - Generated by Multi-PDF Topic Extractor');
        lines.push('================================================================');
        return lines.join('\n');
    }

    function downloadTextFile(filename, content) {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function copyToClipboard(text, targetBtn, successLabel = '') {
        navigator.clipboard.writeText(text).then(() => {
            const originalTitle = targetBtn.getAttribute('title');
            targetBtn.style.color = '#34d399';
            if (successLabel) {
                const originalText = targetBtn.innerText;
                targetBtn.innerText = successLabel;
                setTimeout(() => {
                    targetBtn.innerText = originalText;
                    targetBtn.style.color = '';
                }, 2000);
            } else {
                targetBtn.setAttribute('title', 'Copied to clipboard!');
                setTimeout(() => {
                    targetBtn.style.color = '';
                    targetBtn.setAttribute('title', originalTitle || '');
                }, 1500);
            }
        }).catch(err => {
            console.error('Could not copy text: ', err);
        });
    }

    // =========================================================================
    // 7. Explainer Toggle
    // =========================================================================

    btnToggleExplainer.addEventListener('click', () => {
        const isHidden = explainerContent.style.display === 'none';
        explainerContent.style.display = isHidden ? 'block' : 'none';
        explainerChevron.classList.toggle('open', isHidden);
    });

    // =========================================================================
    // 8. Alerts & Utilities
    // =========================================================================

    function showAlert(message, type = 'error') {
        alertMessage.textContent = message;
        alertBox.style.display = 'flex';
        alertBox.style.borderColor = type === 'warning' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(244, 63, 94, 0.4)';
        alertBox.style.background = type === 'warning' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(244, 63, 94, 0.12)';
        alertBox.style.color = type === 'warning' ? '#fde68a' : '#fecdd3';
    }

    function hideAlert() {
        alertBox.style.display = 'none';
    }

    btnAlertClose.addEventListener('click', hideAlert);

    function formatBytes(bytes, decimals = 1) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[m];
        });
    }

    function escapeAttribute(str) {
        if (!str) return '';
        return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
});
