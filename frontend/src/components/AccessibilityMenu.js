import React, {useState, useEffect, useRef} from 'react';
import {createPortal} from 'react-dom';
import {useLanguage} from '../translations';
import useDisclosure from './useDisclosure';
import './AccessibilityMenu.css';

const STORAGE_KEY = 'sinac_accesibilidad';
const PANEL_ID = 'sinac-panel-accesibilidad';
export const READING_GUIDE_EVENT = 'sinac:guia-lectura';
const FONT_MIN = 80;
const FONT_MAX = 200;
const FONT_STEP = 10;
const SPEECH_LOCALES = {es: 'es-MX', en: 'en-US', de: 'de-DE', zh: 'zh-CN', pt: 'pt-BR'};
const READABLE_SELECTOR = 'button, a, input, select, textarea, label, h1, h2, h3, h4, h5, h6, p, li, td, th, img, [role], [aria-label]';
const MAX_SPOKEN_CHARS = 600;

const speechSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

const DISPLAY_OPTIONS = [
  {key: 'readingMode', attribute: 'data-reading-mode', label: 'a11y.readingMode'},
  {key: 'readingGuide', attribute: 'data-reading-guide', label: 'a11y.readingGuide'},
  {key: 'grayscale', attribute: 'data-grayscale', label: 'a11y.grayscale'},
  {key: 'textSpacing', attribute: 'data-text-spacing', label: 'a11y.textSpacing'},
  {key: 'readableFont', attribute: 'data-readable-font', label: 'a11y.readableFont'},
  {key: 'highlightLinks', attribute: 'data-highlight-links', label: 'a11y.highlightLinks'},
  {key: 'pauseAnimations', attribute: 'data-pause-animations', label: 'a11y.pauseAnimations'},
];

const DEFAULT_SETTINGS = {
  fontScale: 100, highContrast: false, screenReader: false,
  ...Object.fromEntries(DISPLAY_OPTIONS.map(option => [option.key, false])),
};

function loadSettings(){
  const defaults = DEFAULT_SETTINGS;
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return {...defaults, ...stored, screenReader: speechSupported && Boolean(stored.screenReader)};
  } catch (e) {
    return defaults;
  }
}

function clampScale(value){
  return Math.min(FONT_MAX, Math.max(FONT_MIN, value));
}

function readableText(element){
  if (!element) return '';
  const labelledBy = element.getAttribute('aria-labelledby');
  const labelled = labelledBy && labelledBy.split(/\s+/).map(id => document.getElementById(id)?.innerText || '').join(' ');
  if (labelled && labelled.trim()) return labelled;
  const aria = element.getAttribute('aria-label');
  if (aria) return aria;
  if (element.tagName === 'IMG') return element.alt || '';
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(element.tagName)) {
    const label = element.labels?.[0]?.innerText || element.placeholder || element.name || '';
    const value = element.type === 'password' ? '' : (element.tagName === 'SELECT' ? element.selectedOptions?.[0]?.text : element.value);
    return [label, value].filter(Boolean).join(': ');
  }
  return element.innerText || element.textContent || '';
}

function splitIntoChunks(text){
  return text
    .replace(/\s+\n/g, '\n')
    .split(/(?<=[.!?;:\n])\s+/)
    .map(part => part.trim())
    .filter(Boolean);
}

function AccessibilityIcon(){
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="6.4" r="1.7" fill="currentColor" />
      <path d="M6.5 9.3c1.9.6 3.7.9 5.5.9s3.6-.3 5.5-.9" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M12 10.3v3.6M12 13.9l-2.4 4.6M12 13.9l2.4 4.6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function ReadingGuide(){
  const [position, setPosition] = useState(160);

  useEffect(() => {
    const fromPointer = event => setPosition(event.clientY);
    const fromFocus = event => {
      const rect = event.target?.getBoundingClientRect?.();
      if (rect) setPosition(rect.top + Math.min(rect.height / 2, 28));
    };
    window.addEventListener('pointermove', fromPointer, {passive: true});
    document.addEventListener('focusin', fromFocus);
    return () => {
      window.removeEventListener('pointermove', fromPointer);
      document.removeEventListener('focusin', fromFocus);
    };
  }, []);

  return (
    <div className="reading-guide" style={{'--reading-guide-y': `${position}px`}} aria-hidden="true">
      <span className="reading-guide__line" />
    </div>
  );
}

export default function AccessibilityMenu(){
  const {t, language} = useLanguage();
  const panel = useDisclosure();
  const [settings, setSettings] = useState(loadSettings);
  const [announcement, setAnnouncement] = useState('');
  const [speechState, setSpeechState] = useState('idle');
  const lastSpoken = useRef('');
  const readRun = useRef(0);

  useEffect(() => {
    const root = document.documentElement;
    root.style.fontSize = settings.fontScale === 100 ? '' : `${settings.fontScale}%`;
    if (settings.highContrast) root.setAttribute('data-contrast', 'high');
    else root.removeAttribute('data-contrast');
    DISPLAY_OPTIONS.forEach(option => {
      if (settings[option.key]) root.setAttribute(option.attribute, '');
      else root.removeAttribute(option.attribute);
    });
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch (e) {}
  }, [settings]);

  useEffect(() => {
    if (!speechSupported) return undefined;
    window.speechSynthesis.cancel();
    setSpeechState('idle');
    return () => window.speechSynthesis.cancel();
  }, [language]);

  function speak(text, {queue = false} = {}){
    if (!speechSupported) return null;
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return null;
    if (!queue) window.speechSynthesis.cancel();
    const locale = SPEECH_LOCALES[language] || 'es-MX';
    const voice = window.speechSynthesis.getVoices().find(item => item.lang?.toLowerCase().startsWith(locale.slice(0, 2)));
    const utterance = new SpeechSynthesisUtterance(clean.slice(0, MAX_SPOKEN_CHARS));
    utterance.lang = locale;
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
    return utterance;
  }

  const speakRef = useRef(speak);
  speakRef.current = speak;

  useEffect(() => {
    if (!settings.screenReader) return undefined;
    function readTarget(event){
      if (event.target?.closest?.('[data-speech-control]')) return;
      const element = event.target?.closest?.(READABLE_SELECTOR);
      const text = readableText(element);
      if (!text || (event.type === 'focusin' && text === lastSpoken.current)) return;
      lastSpoken.current = text;
      readRun.current += 1;
      setSpeechState('idle');
      speakRef.current(text);
    }
    document.addEventListener('focusin', readTarget);
    document.addEventListener('click', readTarget);
    return () => {
      document.removeEventListener('focusin', readTarget);
      document.removeEventListener('click', readTarget);
      window.speechSynthesis.cancel();
    };
  }, [settings.screenReader]);

  useEffect(() => {
    function enableGuide(){
      setSettings(current => ({...current, readingGuide: true}));
      setAnnouncement(`${t('a11y.readingGuide')}: ${t('a11y.on')}`);
    }
    window.addEventListener(READING_GUIDE_EVENT, enableGuide);
    return () => window.removeEventListener(READING_GUIDE_EVENT, enableGuide);
  }, [t]);

  function update(changes, message){
    setSettings(current => ({...current, ...changes}));
    setAnnouncement(message);
  }

  function toggleScreenReader(){
    const enabled = !settings.screenReader;
    update({screenReader: enabled}, enabled ? t('a11y.readerOn') : t('a11y.readerOff'));
    if (enabled) speak(t('a11y.readerOn'));
    else stopReading();
  }

  function readPage(){
    const main = document.getElementById('contenido-principal');
    const chunks = splitIntoChunks(main?.innerText || '');
    if (!chunks.length) return;
    window.speechSynthesis.cancel();
    const run = ++readRun.current;
    let last = null;
    chunks.forEach(chunk => { last = speak(chunk, {queue: true}) || last; });
    if (last) {
      const finish = () => { if (readRun.current === run) setSpeechState('idle'); };
      last.onend = finish;
      last.onerror = finish;
    }
    setSpeechState('speaking');
    setAnnouncement(t('a11y.speaking'));
  }

  function pauseReading(){
    if (speechState !== 'speaking') return;
    window.speechSynthesis.pause();
    setSpeechState('paused');
    setAnnouncement(t('a11y.paused'));
  }

  function resumeReading(){
    if (speechState !== 'paused') return;
    window.speechSynthesis.resume();
    setSpeechState('speaking');
    setAnnouncement(t('a11y.speaking'));
  }

  function stopReading(){
    readRun.current += 1;
    if (speechSupported) window.speechSynthesis.cancel();
    setSpeechState('idle');
  }

  function changeFont(delta){
    const next = delta === 0 ? 100 : clampScale(settings.fontScale + delta);
    update({fontScale: next}, `${t('a11y.fontSize')}: ${next}%`);
  }

  function toggleContrast(){
    const enabled = !settings.highContrast;
    update({highContrast: enabled}, enabled ? t('a11y.contrastOn') : t('a11y.contrastOff'));
  }

  function toggleDisplayOption(option){
    const enabled = !settings[option.key];
    update({[option.key]: enabled}, `${t(option.label)}: ${enabled ? t('a11y.on') : t('a11y.off')}`);
  }

  function resetAll(){
    stopReading();
    update(DEFAULT_SETTINGS, t('a11y.resetDone'));
  }

  const customized = Object.keys(DEFAULT_SETTINGS).some(key => settings[key] !== DEFAULT_SETTINGS[key]);
  const speechActive = speechState !== 'idle';

  const floating = (settings.readingGuide || speechActive) && createPortal(
    <>
      {settings.readingGuide && <ReadingGuide />}
      {settings.readingGuide && (
        <div className={`a11y-float a11y-float--guide ${speechActive ? '' : 'is-solo'}`}>
          <span>{t('a11y.readingGuide')}</span>
          <button type="button" onClick={() => update({readingGuide: false}, `${t('a11y.readingGuide')}: ${t('a11y.off')}`)}>
            <span aria-hidden="true">✕</span> {t('a11y.guideOff')}
          </button>
        </div>
      )}
      {speechActive && (
        <div className="a11y-float a11y-float--speech" role="region" aria-label={t('a11y.transportLabel')} data-speech-control>
          <span>{speechState === 'speaking' ? t('a11y.speaking') : t('a11y.paused')}</span>
          <div className="a11y-float__actions">
            <button type="button" onClick={stopReading}><span aria-hidden="true">■</span> {t('a11y.stopReading')}</button>
            {speechState === 'speaking'
              ? <button type="button" onClick={pauseReading}><span aria-hidden="true">❚❚</span> {t('a11y.pause')}</button>
              : <button type="button" onClick={resumeReading}><span aria-hidden="true">▶</span> {t('a11y.resume')}</button>}
          </div>
        </div>
      )}
    </>,
    document.body
  );

  return (
    <div className="a11y-menu" ref={panel.wrapperRef} onBlur={panel.onWrapperBlur}>
      <button
        type="button"
        ref={panel.triggerRef}
        className={`a11y-trigger ${customized ? 'is-customized' : ''}`}
        aria-label={t('a11y.open')}
        title={t('a11y.open')}
        aria-expanded={panel.open}
        aria-controls={PANEL_ID}
        onClick={() => panel.toggle('first')}
        onKeyDown={panel.onTriggerKeyDown}
      >
        <AccessibilityIcon />
      </button>
      <div className="a11y-sr-only" role="status" aria-live="polite">{announcement}</div>
      {floating}
      {panel.open && (
        <div
          id={PANEL_ID}
          ref={panel.listRef}
          className="a11y-panel"
          role="group"
          aria-labelledby={`${PANEL_ID}-titulo`}
        >
          <p className="a11y-panel-title" id={`${PANEL_ID}-titulo`}>{t('a11y.title')}</p>

          <div className="a11y-section">
            <p className="a11y-section-label" id={`${PANEL_ID}-lectura`}>{t('a11y.screenReader')}</p>
            {speechSupported ? (
              <div className="a11y-row" role="group" aria-labelledby={`${PANEL_ID}-lectura`}>
                <button type="button" className="a11y-switch" aria-pressed={settings.screenReader} onClick={toggleScreenReader}>
                  <span className="a11y-check" aria-hidden="true"><span className="a11y-check-mark" /></span>
                  {t('a11y.readAloud')}
                </button>
                <button type="button" className="a11y-action" data-speech-control onClick={readPage}>{t('a11y.readPage')}</button>
                <button type="button" className="a11y-action" data-speech-control onClick={pauseReading} disabled={speechState !== 'speaking'}>{t('a11y.pause')}</button>
                <button type="button" className="a11y-action" data-speech-control onClick={resumeReading} disabled={speechState !== 'paused'}>{t('a11y.resume')}</button>
                <button type="button" className="a11y-action" data-speech-control onClick={stopReading}>{t('a11y.stopReading')}</button>
              </div>
            ) : (
              <p className="a11y-note">{t('a11y.readerUnsupported')}</p>
            )}
            {settings.screenReader && <p className="a11y-note">{t('a11y.readerHint')}</p>}
          </div>

          <div className="a11y-section">
            <p className="a11y-section-label" id={`${PANEL_ID}-letra`}>{t('a11y.fontSize')}</p>
            <div className="a11y-row a11y-font-row" role="group" aria-labelledby={`${PANEL_ID}-letra`}>
              <button type="button" className="a11y-action a11y-font-btn" onClick={() => changeFont(-FONT_STEP)} disabled={settings.fontScale <= FONT_MIN}>
                <span aria-hidden="true">A−</span><span className="a11y-sr-only">{t('a11y.fontDecrease')}</span>
              </button>
              <span className="a11y-font-value" aria-hidden="true">{settings.fontScale}%</span>
              <button type="button" className="a11y-action a11y-font-btn" onClick={() => changeFont(FONT_STEP)} disabled={settings.fontScale >= FONT_MAX}>
                <span aria-hidden="true">A+</span><span className="a11y-sr-only">{t('a11y.fontIncrease')}</span>
              </button>
              <button type="button" className="a11y-action" onClick={() => changeFont(0)} disabled={settings.fontScale === 100}>{t('a11y.fontReset')}</button>
            </div>
          </div>

          <div className="a11y-section">
            <p className="a11y-section-label">{t('a11y.contrastSection')}</p>
            <button type="button" className="a11y-switch" aria-pressed={settings.highContrast} onClick={toggleContrast}>
              <span className="a11y-check" aria-hidden="true"><span className="a11y-check-mark" /></span>
              {t('a11y.contrast')}
            </button>
          </div>

          <div className="a11y-section">
            <p className="a11y-section-label">{t('a11y.displaySection')}</p>
            <div className="a11y-switch-list">
              {DISPLAY_OPTIONS.map(option => (
                <button key={option.key} type="button" className="a11y-switch" aria-pressed={settings[option.key]} onClick={() => toggleDisplayOption(option)}>
                  <span className="a11y-check" aria-hidden="true"><span className="a11y-check-mark" /></span>
                  {t(option.label)}
                </button>
              ))}
            </div>
          </div>

          <button type="button" className="a11y-reset" onClick={resetAll}>{t('a11y.resetAll')}</button>
        </div>
      )}
    </div>
  );
}
