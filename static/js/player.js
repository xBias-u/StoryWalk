(function () {
  const players = document.querySelectorAll('[data-player]');

  function formatTime(sec) {
    if (!Number.isFinite(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  async function sendEvent(payload) {
    try {
      await fetch('/api/audio-events/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken') || '',
        },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      // noop for MVP
    }
  }

  players.forEach((root) => {
    const audio = root.querySelector('[data-audio]');
    const playBtn = root.querySelector('[data-play]');
    const rate = root.querySelector('[data-rate]');
    const progress = root.querySelector('[data-progress]');
    const time = root.querySelector('[data-time]');
    const duration = root.querySelector('[data-duration]');
    const locationId = Number(root.dataset.locationId || 0);

    let lastProgressSentAt = 0;

    function currentPayload(eventType) {
      const dur = Number(audio.duration || 0);
      const cur = Number(audio.currentTime || 0);
      const completion = dur > 0 ? Math.min(100, (cur / dur) * 100) : 0;
      return {
        location_id: locationId,
        event_type: eventType,
        current_seconds: cur,
        duration_seconds: dur,
        completion_percent: completion,
      };
    }

    playBtn.addEventListener('click', () => {
      if (audio.paused) {
        audio.play();
      } else {
        audio.pause();
      }
    });

    audio.addEventListener('play', () => {
      playBtn.textContent = '⏸ Pause';
      if (locationId) sendEvent(currentPayload('start'));
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

      const now = Date.now();
      if (locationId && now - lastProgressSentAt > 10000) {
        lastProgressSentAt = now;
        sendEvent(currentPayload('progress'));
      }
    });

    audio.addEventListener('ended', () => {
      if (locationId) sendEvent(currentPayload('complete'));
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
