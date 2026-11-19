import {afterEach} from 'vitest';
import {cleanup} from '@testing-library/react';

if (!window.matchMedia) {
  window.matchMedia = query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent: () => false,
  });
}

window.scrollTo = () => {};
HTMLCanvasElement.prototype.getContext = () => null;
Element.prototype.scrollIntoView = () => {};

afterEach(() => {
  cleanup();
  localStorage.clear();
  document.documentElement.removeAttribute('style');
  for (const name of [...document.documentElement.attributes].map(attr => attr.name)) {
    if (name.startsWith('data-')) document.documentElement.removeAttribute(name);
  }
});
