/**
 * VortexCoder Portfolio — Interactive Features
 * Canvas Particles, Web Audio Drum Sequencer & Procedural Ambient DSP, and SSH Contact Terminal.
 */

document.addEventListener('DOMContentLoaded', () => {
    initMobileNav();
    initCanvasParticles();
    initNovaBeatSequencer();
    initNovaAmbientSynth();
    initAuthModal();
    initLogo3DInteraction();
});

/* =========================================================================
   1. Mobile Navigation Menu
   ========================================================================= */
function initMobileNav() {
    const toggle = document.querySelector('.mobile-toggle');
    const nav = document.querySelector('.nav');
    const links = document.querySelectorAll('.nav-link');

    toggle.addEventListener('click', () => {
        toggle.classList.toggle('open');
        nav.classList.toggle('open');
    });

    links.forEach(link => {
        link.addEventListener('click', () => {
            toggle.classList.remove('open');
            nav.classList.remove('open');
        });
    });

    // Add scroll active highlight
    const sections = document.querySelectorAll('.section');
    window.addEventListener('scroll', () => {
        let current = '';
        const scrollPosition = window.scrollY + 120;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                current = section.getAttribute('id');
            }
        });

        links.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href').substring(1) === current) {
                link.classList.add('active');
            }
        });
    });
}

/* =========================================================================
   2. Canvas Particle Background
   ========================================================================= */
function initCanvasParticles() {
    const canvas = document.getElementById('particle-canvas');
    const ctx = canvas.getContext('2d');

    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    const particles = [];
    // Optimized particle count for buttery smooth rendering (especially on low-end mobile devices)
    const maxParticles = Math.min(45, Math.floor((width * height) / 35000));
    const connectionDist = 120;
    
    const mouse = { x: null, y: null, active: false };

    class Particle {
        constructor() {
            this.reset();
        }

        reset() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
            this.radius = Math.random() * 2 + 1;
            this.alpha = Math.random() * 0.5 + 0.3;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            // Screen boundaries wrap
            if (this.x < 0) this.x = width;
            if (this.x > width) this.x = 0;
            if (this.y < 0) this.y = height;
            if (this.y > height) this.y = 0;

            // Mouse interaction (gravity effect)
            if (mouse.active && mouse.x !== null) {
                const dx = mouse.x - this.x;
                const dy = mouse.y - this.y;
                const distSq = dx * dx + dy * dy;
                if (distSq < 40000) { // 200 * 200
                    const dist = Math.sqrt(distSq);
                    if (dist > 0) {
                        const force = (200 - dist) / 200;
                        this.x += (dx / dist) * force * 0.8;
                        this.y += (dy / dist) * force * 0.8;
                    }
                }
            }
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(6, 182, 212, ${this.alpha})`;
            ctx.fill();
        }
    }

    // Populate particles
    for (let i = 0; i < maxParticles; i++) {
        particles.push(new Particle());
    }

    // Event listeners
    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });

    window.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
        mouse.active = true;
    });

    window.addEventListener('mouseleave', () => {
        mouse.active = false;
    });

    // Draw frame
    function animate() {
        ctx.clearRect(0, 0, width, height);

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            const p1 = particles[i];
            p1.update();
            p1.draw();

            const connectionDistSq = connectionDist * connectionDist;
            for (let j = i + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const distSq = dx * dx + dy * dy;

                if (distSq < connectionDistSq) {
                    // Only calculate square root for nodes that are close enough to draw lines
                    const dist = Math.sqrt(distSq);
                    const alpha = (1 - (dist / connectionDist)) * 0.15;
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = `rgba(168, 85, 247, ${alpha})`;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(animate);
    }

    animate();
}

/* =========================================================================
   3. Web Audio Step-Sequencer (NovaBeat)
   ========================================================================= */
function initNovaBeatSequencer() {
    let audioCtx = null;
    let isPlaying = false;
    let currentStep = 0;
    let nextStepTime = 0.0;
    let timerId = null;

    const bpm = 120;
    const secondsPerBeat = 60.0 / bpm;
    const stepDuration = secondsPerBeat / 2.0; // 8th notes
    const lookahead = 25.0; // ms
    const scheduleAheadTime = 0.1; // sec

    const playBtn = document.getElementById('play-beat');
    const stepsElements = {
        kick: document.querySelectorAll('.seq-row[data-inst="kick"] .step'),
        hat: document.querySelectorAll('.seq-row[data-inst="hat"] .step')
    };

    // Preselected demo beats pattern
    const pattern = {
        kick: [true, false, false, false, true, false, false, false],
        hat: [false, true, true, true, false, true, true, true]
    };

    // Initialize UI active buttons from pattern
    Object.keys(stepsElements).forEach(inst => {
        stepsElements[inst].forEach((el, idx) => {
            if (pattern[inst][idx]) {
                el.classList.add('active');
            }
            el.addEventListener('click', () => {
                pattern[inst][idx] = !pattern[inst][idx];
                el.classList.toggle('active');
                
                // Audition sound if clicked on and context is live
                if (pattern[inst][idx] && audioCtx) {
                    playInstrument(inst, audioCtx.currentTime);
                }
            });
        });
    });

    // Create White Noise buffer once
    let noiseBuffer = null;
    function getNoiseBuffer(ctx) {
        if (noiseBuffer) return noiseBuffer;
        const bufferSize = ctx.sampleRate * 2;
        const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }
        noiseBuffer = buffer;
        return noiseBuffer;
    }

    // Procedural Instruments Synthesis
    function playInstrument(inst, time) {
        if (!audioCtx) return;

        if (inst === 'kick') {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            
            osc.frequency.setValueAtTime(150, time);
            osc.frequency.exponentialRampToValueAtTime(0.01, time + 0.3);
            
            gain.gain.setValueAtTime(1.0, time);
            gain.gain.exponentialRampToValueAtTime(0.01, time + 0.3);
            
            osc.start(time);
            osc.stop(time + 0.3);
        } 
        else if (inst === 'hat') {
            const bufferSource = audioCtx.createBufferSource();
            bufferSource.buffer = getNoiseBuffer(audioCtx);

            const filter = audioCtx.createBiquadFilter();
            filter.type = 'highpass';
            filter.frequency.setValueAtTime(7000, time);

            const gain = audioCtx.createGain();
            gain.gain.setValueAtTime(0.35, time);
            gain.gain.exponentialRampToValueAtTime(0.01, time + 0.05);

            bufferSource.connect(filter);
            filter.connect(gain);
            gain.connect(audioCtx.destination);

            bufferSource.start(time);
            bufferSource.stop(time + 0.06);
        }
    }

    // Sequencer Clock Scheduler
    function scheduler() {
        while (nextStepTime < audioCtx.currentTime + scheduleAheadTime) {
            scheduleStep(currentStep, nextStepTime);
            nextStep();
        }
        timerId = setTimeout(scheduler, lookahead);
    }

    function scheduleStep(step, time) {
        // Visual indicator highlighting columns
        const stepIndex = step;
        audioCtx.createDelay(); // Keep track cleanly
        
        // Execute on main thread with safety timeout
        setTimeout(() => {
            // Remove playing animation class from all steps at this index
            Object.keys(stepsElements).forEach(inst => {
                stepsElements[inst].forEach(el => el.classList.remove('playing'));
                const curEl = stepsElements[inst][stepIndex];
                if (curEl) curEl.classList.add('playing');
            });
        }, Math.max(0, (time - audioCtx.currentTime) * 1000));

        // Play sounds
        if (pattern.kick[step]) playInstrument('kick', time);
        if (pattern.hat[step]) playInstrument('hat', time);
    }

    function nextStep() {
        nextStepTime += stepDuration;
        currentStep = (currentStep + 1) % 8;
    }

    function togglePlay() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }

        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        isPlaying = !isPlaying;

        if (isPlaying) {
            currentStep = 0;
            nextStepTime = audioCtx.currentTime + 0.05;
            playBtn.classList.add('active');
            playBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"></rect></svg>
                Stop
            `;
            scheduler();
            showToast('info', 'NovaBeat sequencer active. Web Audio synth triggered.');
        } else {
            clearTimeout(timerId);
            playBtn.classList.remove('active');
            playBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                Play
            `;
            // Reset active visual states
            Object.keys(stepsElements).forEach(inst => {
                stepsElements[inst].forEach(el => el.classList.remove('playing'));
            });
        }
    }

    playBtn.addEventListener('click', togglePlay);
}

/* =========================================================================
   4. Procedural Ambient Synthesizer (NovaAmbient)
   ========================================================================= */
function initNovaAmbientSynth() {
    let audioCtx = null;
    let isPlaying = false;

    // Node references
    let rainNode = null;
    let fireNode = null;
    let windNode = null;

    let rainGain = null;
    let fireGain = null;
    let windGain = null;
    let masterGain = null;

    let windLfo = null;

    const playBtn = document.getElementById('play-ambient');
    const sliders = {
        rain: document.getElementById('rain-vol'),
        fire: document.getElementById('fire-vol'),
        wind: document.getElementById('wind-vol')
    };

    // Helper: generate White Noise Buffer
    function createNoiseBuffer(ctx, seconds = 2) {
        const bufferSize = ctx.sampleRate * seconds;
        const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }
        return buffer;
    }

    // Synth generators
    function startRain(ctx) {
        // High passed white noise for rain falling hiss
        const rainSource = ctx.createBufferSource();
        rainSource.buffer = createNoiseBuffer(ctx, 3);
        rainSource.loop = true;

        const rainFilter = ctx.createBiquadFilter();
        rainFilter.type = 'bandpass';
        rainFilter.frequency.value = 1000;
        rainFilter.Q.value = 0.5;

        rainGain = ctx.createGain();
        rainGain.gain.value = parseFloat(sliders.rain.value) / 100;

        rainSource.connect(rainFilter);
        rainFilter.connect(rainGain);
        rainGain.connect(masterGain);
        rainSource.start(0);

        return rainSource;
    }

    function startFire(ctx) {
        // Low rumble noise + periodic crackle pops
        const fireSource = ctx.createBufferSource();
        fireSource.buffer = createNoiseBuffer(ctx, 4);
        fireSource.loop = true;

        const fireFilter = ctx.createBiquadFilter();
        fireFilter.type = 'lowpass';
        fireFilter.frequency.value = 120; // deep wood crackle rumble

        fireGain = ctx.createGain();
        fireGain.gain.value = parseFloat(sliders.fire.value) / 100;

        fireSource.connect(fireFilter);
        fireFilter.connect(fireGain);
        fireGain.connect(masterGain);
        fireSource.start(0);

        // Procedural timber crackles via scheduled nodes
        const crackleInterval = setInterval(() => {
            if (!isPlaying || !audioCtx) {
                clearInterval(crackleInterval);
                return;
            }
            if (sliders.fire.value > 0) {
                const popVol = (parseFloat(sliders.fire.value) / 100) * (Math.random() * 0.4 + 0.1);
                
                const clickOsc = ctx.createOscillator();
                const clickGain = ctx.createGain();
                clickOsc.type = 'triangle';
                clickOsc.frequency.setValueAtTime(Math.random() * 2000 + 400, ctx.currentTime);
                
                clickGain.gain.setValueAtTime(popVol, ctx.currentTime);
                clickGain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + Math.random() * 0.03 + 0.005);
                
                clickOsc.connect(clickGain);
                clickGain.connect(masterGain);
                
                clickOsc.start();
                clickOsc.stop(ctx.currentTime + 0.04);
            }
        }, 120);

        return fireSource;
    }

    function startWind(ctx) {
        // Dynamic LFO modulated bandpassed noise
        const windSource = ctx.createBufferSource();
        windSource.buffer = createNoiseBuffer(ctx, 5);
        windSource.loop = true;

        const windFilter = ctx.createBiquadFilter();
        windFilter.type = 'bandpass';
        windFilter.frequency.value = 350;
        windFilter.Q.value = 3;

        // Modulator LFO to sweep bandpass frequency to create gusting wind effect
        windLfo = ctx.createOscillator();
        windLfo.frequency.value = 0.08; // Very slow 12-second cycles

        const lfoGain = ctx.createGain();
        lfoGain.gain.value = 180; // Modulate frequency by +/- 180Hz

        windLfo.connect(lfoGain);
        lfoGain.connect(windFilter.frequency);
        windLfo.start(0);

        windGain = ctx.createGain();
        windGain.gain.value = parseFloat(sliders.wind.value) / 100;

        windSource.connect(windFilter);
        windFilter.connect(windGain);
        windGain.connect(masterGain);
        windSource.start(0);

        return windSource;
    }

    function togglePlay() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }

        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        isPlaying = !isPlaying;

        if (isPlaying) {
            // Enable controls
            Object.values(sliders).forEach(s => s.removeAttribute('disabled'));

            masterGain = audioCtx.createGain();
            masterGain.gain.value = 0.8;
            masterGain.connect(audioCtx.destination);

            rainNode = startRain(audioCtx);
            fireNode = startFire(audioCtx);
            windNode = startWind(audioCtx);

            playBtn.classList.add('active');
            playBtn.textContent = 'Pause Sounds';
            showToast('success', 'NovaAmbient synth engine online. Drag sliders to blend atmospheres.');
        } else {
            // Disable controls
            Object.values(sliders).forEach(s => s.setAttribute('disabled', 'true'));

            if (rainNode) { try { rainNode.stop(); } catch(e){} }
            if (fireNode) { try { fireNode.stop(); } catch(e){} }
            if (windNode) { try { windNode.stop(); } catch(e){} }
            if (windLfo) { try { windLfo.stop(); } catch(e){} }

            playBtn.classList.remove('active');
            playBtn.textContent = 'Play Sounds';
        }
    }

    // Attach listeners
    playBtn.addEventListener('click', togglePlay);

    sliders.rain.addEventListener('input', () => {
        if (rainGain) rainGain.gain.setValueAtTime(parseFloat(sliders.rain.value) / 100, audioCtx.currentTime);
    });
    sliders.fire.addEventListener('input', () => {
        if (fireGain) fireGain.gain.setValueAtTime(parseFloat(sliders.fire.value) / 100, audioCtx.currentTime);
    });
    sliders.wind.addEventListener('input', () => {
        if (windGain) windGain.gain.setValueAtTime(parseFloat(sliders.wind.value) / 100, audioCtx.currentTime);
    });
}



/* =========================================================================
   6. UI Utility functions
   ========================================================================= */
function showToast(type, text) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    toast.innerHTML = `
        <span class="toast-content">${text}</span>
        <button class="toast-close">&times;</button>
    `;
    
    container.appendChild(toast);

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.remove();
    });

    // Auto dismiss
    setTimeout(() => {
        toast.style.animation = 'toast-in 0.3s reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

/* =========================================================================
   7. Glassmorphic Auth Modal (Sign In / Sign Up)
   ========================================================================= */
function initAuthModal() {
    const modal = document.getElementById('auth-modal');
    const closeBtn = document.getElementById('auth-modal-close');
    
    const signinTriggers = [
        document.getElementById('signin-trigger'),
        document.getElementById('mobile-signin-trigger')
    ];
    const signupTriggers = [
        document.getElementById('signup-trigger'),
        document.getElementById('mobile-signup-trigger')
    ];

    const tabSignin = document.getElementById('tab-signin-btn');
    const tabSignup = document.getElementById('tab-signup-btn');
    
    const signinForm = document.getElementById('signin-form');
    const signupForm = document.getElementById('signup-form');
    const log = document.getElementById('auth-terminal-log');

    // Profile elements
    const profileModal = document.getElementById('profile-modal');
    const profileCloseBtn = document.getElementById('profile-modal-close');
    const profileTrigger = document.getElementById('profile-trigger');
    const mobileProfileTrigger = document.getElementById('mobile-profile-trigger');
    const logoutBtn = document.getElementById('btn-logout');

    function printAuthLog(text, styleClass = '') {
        const p = document.createElement('p');
        p.className = `auth-log-line ${styleClass}`;
        p.textContent = text;
        log.appendChild(p);
        log.scrollTop = log.scrollHeight;
    }

    function openModal(tab = 'signin') {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; // Prevent background scroll
        switchTab(tab);
    }

    function closeModal() {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        signinForm.reset();
        signupForm.reset();
        log.innerHTML = '<p class="auth-log-line text-muted">> Idle. Awaiting authentication inputs...</p>';
    }

    function switchTab(tab) {
        if (tab === 'signin') {
            tabSignin.classList.add('active');
            tabSignup.classList.remove('active');
            signinForm.classList.remove('hidden');
            signupForm.classList.add('hidden');
        } else {
            tabSignin.classList.remove('active');
            tabSignup.classList.add('active');
            signinForm.classList.add('hidden');
            signupForm.classList.remove('hidden');
        }
    }

    // Attach open triggers
    signinTriggers.forEach(t => {
        if (t) t.addEventListener('click', () => openModal('signin'));
    });
    signupTriggers.forEach(t => {
        if (t) t.addEventListener('click', () => openModal('signup'));
    });

    closeBtn.addEventListener('click', closeModal);
    
    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Tab buttons
    tabSignin.addEventListener('click', () => switchTab('signin'));
    tabSignup.addEventListener('click', () => switchTab('signup'));

    // Update Header UI based on login state
    function updateAuthUI() {
        const activeUser = sessionStorage.getItem('vortexcoder_active_user');
        const signinBtn = document.getElementById('signin-trigger');
        const signupBtn = document.getElementById('signup-trigger');
        const profileBtn = document.getElementById('profile-trigger');

        const mobileSigninBtn = document.getElementById('mobile-signin-trigger');
        const mobileSignupBtn = document.getElementById('mobile-signup-trigger');
        const mobileProfileBtn = document.getElementById('mobile-profile-trigger');

        if (activeUser) {
            if (signinBtn) signinBtn.classList.add('hidden');
            if (signupBtn) signupBtn.classList.add('hidden');
            if (mobileSigninBtn) mobileSigninBtn.classList.add('hidden');
            if (mobileSignupBtn) mobileSignupBtn.classList.add('hidden');

            if (profileBtn) {
                profileBtn.classList.remove('hidden');
                document.getElementById('profile-btn-text').textContent = activeUser;
            }
            if (mobileProfileBtn) {
                mobileProfileBtn.classList.remove('hidden');
                document.getElementById('mobile-profile-btn-text').textContent = activeUser;
            }
        } else {
            if (signinBtn) signinBtn.classList.remove('hidden');
            if (signupBtn) signupBtn.classList.remove('hidden');
            if (mobileSigninBtn) mobileSigninBtn.classList.remove('hidden');
            if (mobileSignupBtn) mobileSignupBtn.classList.remove('hidden');

            if (profileBtn) profileBtn.classList.add('hidden');
            if (mobileProfileBtn) mobileProfileBtn.classList.add('hidden');
        }
    }

    // Profile Modal Actions
    function openProfileModal() {
        const activeUser = sessionStorage.getItem('vortexcoder_active_user');
        if (!activeUser) return;

        const users = JSON.parse(localStorage.getItem('vortexcoder_users') || '{}');
        const userData = users[activeUser];

        if (userData) {
            const displayCallsign = document.getElementById('profile-display-callsign');
            const displaySerial = document.getElementById('profile-display-serial');
            const displayRegDate = document.getElementById('profile-stat-reg-date');
            const displayDownloads = document.getElementById('profile-stat-downloads');

            if (displayCallsign) displayCallsign.textContent = activeUser;
            
            const serialNum = (typeof userData === 'string') ? 1 : (userData.serialNumber || 1);
            const formattedSerial = String(serialNum).padStart(4, '0');
            if (displaySerial) displaySerial.textContent = `SERIAL: #${formattedSerial}`;
            
            const regDate = (typeof userData === 'string') ? '24.05.2026 12:00:00' : (userData.registeredAt || '-');
            if (displayRegDate) displayRegDate.textContent = regDate;
            
            const dls = (typeof userData === 'string') ? 0 : (userData.downloads || 0);
            if (displayDownloads) displayDownloads.textContent = dls;
        }

        profileModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    function closeProfileModal() {
        profileModal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    if (profileTrigger) profileTrigger.addEventListener('click', openProfileModal);
    if (mobileProfileTrigger) mobileProfileTrigger.addEventListener('click', openProfileModal);
    if (profileCloseBtn) profileCloseBtn.addEventListener('click', closeProfileModal);
    if (profileModal) {
        profileModal.addEventListener('click', (e) => {
            if (e.target === profileModal) closeProfileModal();
        });
    }

    // Logout
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            sessionStorage.removeItem('vortexcoder_active_user');
            closeProfileModal();
            updateAuthUI();
            showToast('info', 'Secure session terminated (logged out).');
        });
    }

    // Login handler
    signinForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('signin-username').value.trim();
        const password = document.getElementById('signin-password').value;
        
        log.innerHTML = ''; // Clear logs
        printAuthLog('> Initializing authorization sequence...');
        await new Promise(r => setTimeout(r, 400));
        printAuthLog(`> Verifying Callsign "${username}" against directory database...`);
        await new Promise(r => setTimeout(r, 600));
        printAuthLog('> Checking encrypted passkey signature hash...');
        await new Promise(r => setTimeout(r, 500));
        
        const users = JSON.parse(localStorage.getItem('vortexcoder_users') || '{}');
        
        // Add a default guest user so they can log in even if they didn't register!
        if (Object.keys(users).length === 0) {
            users['guest'] = {
                password: 'password',
                registeredAt: '24.05.2026 12:00:00',
                serialNumber: 1,
                downloads: 3
            };
            localStorage.setItem('vortexcoder_users', JSON.stringify(users));
        }

        const userData = users[username];
        const isValid = userData && (typeof userData === 'string' ? userData === password : userData.password === password);

        if (isValid) {
            // Upgrade legacy string to object if necessary
            if (typeof userData === 'string') {
                users[username] = {
                    password: password,
                    registeredAt: '24.05.2026 12:00:00',
                    serialNumber: Object.keys(users).indexOf(username) + 1,
                    downloads: 0
                };
                localStorage.setItem('vortexcoder_users', JSON.stringify(users));
            }

            sessionStorage.setItem('vortexcoder_active_user', username);
            printAuthLog('[OK] Handshake verified. Access granted.', 'text-success');
            printAuthLog(`> Welcome back, Operator ${username}! Secure uplink established.`, 'text-success');
            showToast('success', `Access granted! Welcome back, ${username}.`);
            await new Promise(r => setTimeout(r, 1000));
            closeModal();
            updateAuthUI();
        } else {
            printAuthLog('[ERR] Handshake failed: Invalid Operator Callsign or Passkey.', 'text-error');
            showToast('error', 'Login failed: Invalid credentials.');
        }
    });

    // Registration handler
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('signup-username').value.trim();
        const password = document.getElementById('signup-password').value;

        if (username.length < 3) {
            showToast('error', 'Callsign must be at least 3 characters.');
            return;
        }

        log.innerHTML = ''; // Clear logs
        printAuthLog('> Registering new operator protocols...');
        await new Promise(r => setTimeout(r, 400));
        printAuthLog('> Contacting local secure sector directory database..._');
        await new Promise(r => setTimeout(r, 600));
        printAuthLog(`> Verifying uniqueness of callsign: ${username}...`);
        await new Promise(r => setTimeout(r, 500));

        const users = JSON.parse(localStorage.getItem('vortexcoder_users') || '{}');

        // Initialize default guest if empty so that guest remains Serial #0001
        if (Object.keys(users).length === 0) {
            users['guest'] = {
                password: 'password',
                registeredAt: '24.05.2026 12:00:00',
                serialNumber: 1,
                downloads: 3
            };
        }

        if (users[username]) {
            printAuthLog(`[ERR] Registration failed: Callsign "${username}" is already claimed by another operator.`, 'text-error');
            showToast('error', 'Registration failed: Callsign already exists.');
        } else {
            // Save to local storage
            users[username] = {
                password: password,
                registeredAt: new Date().toLocaleDateString('ru-RU') + ' ' + new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                serialNumber: Object.keys(users).length + 1,
                downloads: 0
            };
            localStorage.setItem('vortexcoder_users', JSON.stringify(users));

            printAuthLog('[OK] Unique signature generated.', 'text-success');
            printAuthLog(`> Registered Operator "${username}" successfully.`, 'text-success');
            showToast('success', `Operator ${username} registered successfully!`);
            await new Promise(r => setTimeout(r, 1200));
            
            // Switch to signin tab automatically
            switchTab('signin');
            document.getElementById('signin-username').value = username; // Pre-fill username
            document.getElementById('signin-password').focus();
            printAuthLog('> Switched to Sign In. Please verify your credentials to establish uplink.');
        }
    });

    // Session time tracking
    let sessionStartTime = Date.now();
    setInterval(() => {
        const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
        const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        const timeEl = document.getElementById('profile-stat-time');
        if (timeEl) timeEl.textContent = `${h}:${m}:${s}`;
    }, 1000);

    // Downloads tracking
    document.querySelectorAll('.download-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const activeUser = sessionStorage.getItem('vortexcoder_active_user');
            if (activeUser) {
                const users = JSON.parse(localStorage.getItem('vortexcoder_users') || '{}');
                const userData = users[activeUser];
                if (userData) {
                    if (typeof userData === 'string') {
                        users[activeUser] = {
                            password: userData,
                            registeredAt: '24.05.2026 12:00:00',
                            serialNumber: 1,
                            downloads: 0
                        };
                    }
                    users[activeUser].downloads = (users[activeUser].downloads || 0) + 1;
                    localStorage.setItem('vortexcoder_users', JSON.stringify(users));
                    
                    const dlEl = document.getElementById('profile-stat-downloads');
                    if (dlEl) dlEl.textContent = users[activeUser].downloads;
                }
            }
        });
    });

    // Run initial UI state check
    updateAuthUI();
}

/* =========================================================================
   8. 3D Logo Interactive Rotation & Click Spin
   ========================================================================= */
function initLogo3DInteraction() {
    const container = document.querySelector('.logo-sphere-container');
    const avatar = document.querySelector('.hero-avatar');
    if (!container || !avatar) return;

    // 3D tilt tracking on mousemove
    container.addEventListener('mousemove', (e) => {
        const rect = container.getBoundingClientRect();
        
        // Coordinates relative to the center of the container
        const x = e.clientX - rect.left - (rect.width / 2);
        const y = e.clientY - rect.top - (rect.height / 2);
        
        // Calculate angles (max ~20 degrees rotation)
        const rx = -(y / (rect.height / 2)) * 20;
        const ry = (x / (rect.width / 2)) * 20;
        
        avatar.style.setProperty('--rx', `${rx}deg`);
        avatar.style.setProperty('--ry', `${ry}deg`);
    });

    // Smooth reset on mouseleave
    container.addEventListener('mouseleave', () => {
        avatar.style.setProperty('--rx', '0deg');
        avatar.style.setProperty('--ry', '0deg');
    });

    // Quick spin spin animation on click
    let currentRotation = 0;
    container.addEventListener('click', () => {
        currentRotation += 360;
        avatar.style.transform = `rotateX(var(--rx, 0deg)) rotateY(calc(var(--ry, 0deg) + ${currentRotation}deg)) scale(1.05)`;
        
        showToast('info', 'System core spun. Visual sync established.');

        setTimeout(() => {
            avatar.style.transform = `rotateX(var(--rx, 0deg)) rotateY(calc(var(--ry, 0deg) + ${currentRotation}deg)) scale(1)`;
        }, 300);
    });
}
