/**
 * drum2midi Web UI
 */

let config = { apiBaseUrl: 'http://localhost:8001' };
let currentJobId = null;
let selectedFile = null;

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileName = document.getElementById('file-name');
const processBtn = document.getElementById('process-btn');
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const resultSection = document.getElementById('result-section');
const errorSection = document.getElementById('error-section');
const statusText = document.getElementById('status-text');
const resultInfo = document.getElementById('result-info');
const errorMessage = document.getElementById('error-message');
const downloadBtn = document.getElementById('download-btn');
const newBtn = document.getElementById('new-btn');
const retryBtn = document.getElementById('retry-btn');

// Load config
async function loadConfig() {
  try {
    const response = await fetch('config.json');
    if (response.ok) {
      config = await response.json();
      console.log('Config loaded:', config);
    }
  } catch (e) {
    console.warn('Could not load config.json, using defaults');
  }
}

// Initialize
loadConfig();

// File handling
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');

  const files = e.dataTransfer.files;
  if (files.length > 0) {
    handleFile(files[0]);
  }
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    handleFile(e.target.files[0]);
  }
});

function handleFile(file) {
  if (!file.name.toLowerCase().endsWith('.wav') && !file.name.toLowerCase().endsWith('.wave')) {
    alert('Please select a WAV file');
    return;
  }

  selectedFile = file;
  fileName.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  processBtn.disabled = false;
}

// Process button
processBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  showSection('progress');
  statusText.textContent = 'Uploading...';

  try {
    // Get options
    const stemsSelect = document.getElementById('stems');
    const stems = Array.from(stemsSelect.selectedOptions).map(o => o.value).join(',');
    const bpm = document.getElementById('bpm').value || 'auto';
    const sepBackend = document.getElementById('sep-backend').value;
    const sepQuality = document.getElementById('sep-quality').value;

    // Create form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('stems', stems);
    formData.append('bpm', bpm);
    formData.append('sep_backend', sepBackend);
    formData.append('sep_quality', sepQuality);

    // Submit job
    const response = await fetch(`${config.apiBaseUrl}/api/jobs`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create job');
    }

    const job = await response.json();
    currentJobId = job.job_id;

    // Poll for status
    statusText.textContent = 'Processing...';
    pollJobStatus();

  } catch (error) {
    showError(error.message);
  }
});

async function pollJobStatus() {
  try {
    const response = await fetch(`${config.apiBaseUrl}/api/jobs/${currentJobId}`);

    if (!response.ok) {
      throw new Error('Failed to get job status');
    }

    const job = await response.json();

    if (job.status === 'completed') {
      showResult(job);
    } else if (job.status === 'failed') {
      showError(job.error || 'Processing failed');
    } else {
      // Still processing, poll again
      statusText.textContent = `Processing... (${job.status})`;
      setTimeout(pollJobStatus, 1000);
    }

  } catch (error) {
    showError(error.message);
  }
}

function showResult(job) {
  showSection('result');

  const result = job.result || {};
  resultInfo.innerHTML = `
    <p><strong>Duration:</strong> ${result.duration || '-'}s</p>
    <p><strong>BPM:</strong> ${result.bpm || '-'}</p>
    <p><strong>Separation:</strong> ${result.separation_method || '-'}</p>
    <p><strong>MIDI Notes:</strong> ${result.total_midi_notes || '-'}</p>
    <p><strong>Stems:</strong> ${(result.stems || []).join(', ')}</p>
  `;
}

function showError(message) {
  showSection('error');
  errorMessage.textContent = message;
}

function showSection(section) {
  uploadSection.classList.add('hidden');
  progressSection.classList.add('hidden');
  resultSection.classList.add('hidden');
  errorSection.classList.add('hidden');

  switch (section) {
    case 'upload':
      uploadSection.classList.remove('hidden');
      break;
    case 'progress':
      progressSection.classList.remove('hidden');
      break;
    case 'result':
      resultSection.classList.remove('hidden');
      break;
    case 'error':
      errorSection.classList.remove('hidden');
      break;
  }
}

// Download button
downloadBtn.addEventListener('click', () => {
  if (currentJobId) {
    window.location.href = `${config.apiBaseUrl}/api/jobs/${currentJobId}/download`;
  }
});

// New/Retry buttons
newBtn.addEventListener('click', resetUI);
retryBtn.addEventListener('click', resetUI);

function resetUI() {
  selectedFile = null;
  currentJobId = null;
  fileName.textContent = '';
  processBtn.disabled = true;
  fileInput.value = '';
  showSection('upload');
}
