(function () {
  const players = document.querySelectorAll('[data-player]');

  function formatTime(sec) {
    if (!Number.isFinite(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  players.forEach((root) => {
    const audio = root.querySelector('[data-audio]');
    const playBtn = root.querySelector('[data-play]');
    const rate = root.querySelector('[data-rate]');
    const progress = root.querySelector('[data-progress]');
    const time = root.querySelector('[data-time]');
    const duration = root.querySelector('[data-duration]');

    playBtn.addEventListener('click', () => {
      if (audio.paused) {
        audio.play();
      } else {
        audio.pause();
      }
    });

    audio.addEventListener('play', () => {
      playBtn.textContent = '⏸ Pause';
    });

    audio.addEventListener('pause', () => {
      playBtn.textContent = '▶ Play';
    });

    audio.addEventListener('loadedmetadata', () => {
      duration.textContent = formatTime(audio.duration);
    });

    audio.addEventListener('timeupdate', () => {
      time.textContent = formatTime(audio.currentTime);
      if (audio.duration) {
        progress.value = Math.round((audio.currentTime / audio.duration) * 100);
      }
    });

    progress.addEventListener('input', () => {
      if (audio.duration) {
        audio.currentTime = (progress.value / 100) * audio.duration;
      }
    });

    rate.addEventListener('change', () => {
      audio.playbackRate = Number(rate.value);
    });
  });
})();
