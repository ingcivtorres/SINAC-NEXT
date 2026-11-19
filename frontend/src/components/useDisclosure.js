import {useState, useEffect, useRef} from 'react';

export function focusableItems(container){
  return container ? Array.from(container.querySelectorAll('button:not([disabled])')) : [];
}

export function handleListKeys(event, container){
  const items = focusableItems(container);
  if (!items.length) return;
  const index = items.indexOf(document.activeElement);
  let next = null;
  if (event.key === 'ArrowDown') next = items[(index + 1) % items.length];
  else if (event.key === 'ArrowUp') next = items[(index - 1 + items.length) % items.length];
  else if (event.key === 'Home') next = items[0];
  else if (event.key === 'End') next = items[items.length - 1];
  if (next) {
    event.preventDefault();
    next.focus();
  }
}

export default function useDisclosure(){
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);
  const triggerRef = useRef(null);
  const listRef = useRef(null);
  const focusOnOpen = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    if (focusOnOpen.current) {
      const items = focusableItems(listRef.current);
      const target = focusOnOpen.current === 'last' ? items[items.length - 1]
        : focusOnOpen.current === 'selected' ? (listRef.current?.querySelector('[aria-pressed="true"]') || items[0])
        : items[0];
      target?.focus();
      focusOnOpen.current = null;
    }
    function closeOnOutsideClick(event) {
      if (!wrapperRef.current?.contains(event.target)) setOpen(false);
    }
    function closeOnEscape(event) {
      if (event.key !== 'Escape') return;
      setOpen(false);
      if (wrapperRef.current?.contains(document.activeElement)) triggerRef.current?.focus();
    }
    const list = listRef.current;
    const moveWithArrows = event => handleListKeys(event, list);
    list?.addEventListener('keydown', moveWithArrows);
    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      list?.removeEventListener('keydown', moveWithArrows);
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [open]);

  function openWithFocus(position){
    focusOnOpen.current = position;
    setOpen(true);
  }

  function onTriggerKeyDown(event){
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      openWithFocus('first');
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      openWithFocus('last');
    }
  }

  function onWrapperBlur(event){
    if (open && !wrapperRef.current?.contains(event.relatedTarget)) setOpen(false);
  }

  function closeAndReturnFocus(){
    setOpen(false);
    triggerRef.current?.focus();
  }

  function toggle(position = 'first'){
    if (open) setOpen(false);
    else openWithFocus(position);
  }

  return {open, setOpen, wrapperRef, triggerRef, listRef, openWithFocus, onTriggerKeyDown, onWrapperBlur, closeAndReturnFocus, toggle};
}
