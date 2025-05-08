// room.js - Create this file in your static/js/ directory

// Timer functionality
let timer;
let seconds = 0;
let timerRunning = false;

function formatTime(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    return [
        hours.toString().padStart(2, '0'),
        minutes.toString().padStart(2, '0'),
        seconds.toString().padStart(2, '0')
    ].join(':');
}

function startTimer() {
    if (!timerRunning) {
        timerRunning = true;
        timer = setInterval(() => {
            seconds++;
            document.getElementById('timer-display').textContent = formatTime(seconds);
        }, 1000);
    }
}

function pauseTimer() {
    clearInterval(timer);
    timerRunning = false;
}

function resetTimer() {
    clearInterval(timer);
    timerRunning = false;
    seconds = 0;
    document.getElementById('timer-display').textContent = '00:00:00';
}

// Music player functionality
let audioPlayer;
let currentTrack = null;
let trackList = [];

function initMusicPlayer() {
    audioPlayer = document.getElementById('audio-player');
    const genreSelector = document.getElementById('music-genre-selector');
    
    // Initialize audio player controls
    document.getElementById('play-pause').addEventListener('click', togglePlayPause);
    
    // Add time update listener
    audioPlayer.addEventListener('timeupdate', updateProgress);
    
    // Add track end listener
    audioPlayer.addEventListener('ended', playNextTrack);
    
    // Add progress bar click handler
    document.querySelector('.progress-bar').addEventListener('click', seekTrack);
    
    // Load initial tracks
    if (genreSelector) {
        loadTracks(genreSelector.value);
        
        // Add genre change listener
        genreSelector.addEventListener('change', function() {
            loadTracks(this.value);
        });
    }
}

function loadTracks(genre) {
    const tracksContainer = document.getElementById('track-list');
    tracksContainer.innerHTML = '<p>Loading tracks...</p>';
    
    fetch(`/rooms/music-tracks/?genre=${genre}`)
        .then(response => response.json())
        .then(data => {
            trackList = data.tracks;
            
            if (trackList.length === 0) {
                tracksContainer.innerHTML = '<p>No tracks available for this genre</p>';
                return;
            }
            
            let trackListHtml = '';
            trackList.forEach((track, index) => {
                trackListHtml += `
                    <div class="track-item" data-index="${index}">
                        <div class="track-info">
                            <span class="track-title">${track.title}</span>
                            <span class="track-artist">${track.artist}</span>
                        </div>
                        <button class="play-track-btn">Play</button>
                    </div>
                `;
            });
            
            tracksContainer.innerHTML = trackListHtml;
            
            // Add event listeners to play buttons
            document.querySelectorAll('.play-track-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const trackIndex = this.parentElement.dataset.index;
                    playTrack(trackIndex);
                });
            });
        })
        .catch(error => {
            console.error('Error loading tracks:', error);
            tracksContainer.innerHTML = '<p>Failed to load tracks. Please try again.</p>';
        });
}

function playTrack(index) {
    if (index >= 0 && index < trackList.length) {
        currentTrack = index;
        const track = trackList[currentTrack];
        
        // Update player display
        document.getElementById('current-track').textContent = `Now playing: ${track.title} - ${track.artist}`;
        
        // Set audio source and play
        audioPlayer.src = track.file_path;
        audioPlayer.play();
        
        // Highlight current track
        document.querySelectorAll('.track-item').forEach((item, i) => {
            item.classList.toggle('active', i === currentTrack);
        });
        
        // Update play/pause button
        document.getElementById('play-pause').textContent = 'Pause';
    }
}

function playNextTrack() {
    if (trackList.length > 0) {
        let nextTrack = (currentTrack + 1) % trackList.length;
        playTrack(nextTrack);
    }
}

function togglePlayPause() {
    if (audioPlayer.paused) {
        if (audioPlayer.src) {
            audioPlayer.play();
            document.getElementById('play-pause').textContent = 'Pause';
        } else if (trackList.length > 0) {
            playTrack(0);
        }
    } else {
        audioPlayer.pause();
        document.getElementById('play-pause').textContent = 'Play';
    }
}

function updateProgress() {
    const currentTime = formatAudioTime(audioPlayer.currentTime);
    const duration = formatAudioTime(audioPlayer.duration || 0);
    
    document.getElementById('current-time').textContent = currentTime;
    document.getElementById('duration').textContent = duration;
    
    // Update progress bar
    const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100 || 0;
    document.querySelector('.progress-fill').style.width = `${progress}%`;
}

function formatAudioTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function seekTrack(event) {
    if (audioPlayer.src) {
        const progressBar = document.querySelector('.progress-bar');
        const rect = progressBar.getBoundingClientRect();
        const pos = (event.clientX - rect.left) / rect.width;
        
        audioPlayer.currentTime = pos * audioPlayer.duration;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const startBtn = document.getElementById('start-timer');
    const pauseBtn = document.getElementById('pause-timer');
    const resetBtn = document.getElementById('reset-timer');
    const summarizeBtn = document.getElementById('summarize-btn');

    if (startBtn && pauseBtn && resetBtn) {
        startBtn.addEventListener('click', startTimer);
        pauseBtn.addEventListener('click', pauseTimer);
        resetBtn.addEventListener('click', resetTimer);
    }

    initMusicPlayer();

    if (summarizeBtn) {
        summarizeBtn.addEventListener('click', summarizeDiscussion);
    }
});


// Summarization functionality
function summarizeDiscussion() {
    const messagesContainer = document.querySelector('.messages-container');
    const messages = Array.from(messagesContainer.querySelectorAll('.message')).map(
        msg => msg.querySelector('.message-content').textContent
    );
    
    if (messages.length === 0) {
        alert('No messages to summarize.');
        return;
    }
    
    fetch('/ai/summarize/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ messages })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }
        
        // Create modal for summary
        const modal = document.createElement('div');
        modal.className = 'summary-modal';
        
        let questionsHtml = '';
        if (data.questions && data.questions.length > 0) {
            questionsHtml = '<h4>Follow-up Questions:</h4><ul>';
            data.questions.forEach(q => {
                questionsHtml += `<li><button class="followup-btn">${q}</button></li>`;
            });
            questionsHtml += '</ul>';
        }
        
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h3>Discussion Summary</h3>
                <p>${data.summary}</p>
                ${questionsHtml}
                <div id="followup-response" style="display:none;">
                    <h4>Response:</h4>
                    <p id="followup-text"></p>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close button functionality
        modal.querySelector('.close').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        // Follow-up question buttons
        modal.querySelectorAll('.followup-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const question = this.textContent;
                askFollowupQuestion(question, messages.join('. '));
            });
        });
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function askFollowupQuestion(question, originalText) {
    fetch('/ai/followup/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ 
            question: question,
            original_text: originalText
        })
    })
    .then(response => response.json())
    .then(data => {
        const responseDiv = document.getElementById('followup-response');
        const responseText = document.getElementById('followup-text');
        
        responseText.textContent = data.answer;
        responseDiv.style.display = 'block';
    })
    .catch(error => {
        console.error('Error:', error);
    });
}