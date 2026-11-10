// A window whose data could not be fetched says so, with a way to try again: without this a
// dropped request drew as empty data ("no shopkeeper here", "0 gold in the bank").
// note(root, failed, retry): shows the line under the window's head when `failed`, clears it when not.
export function netNote(root, failed, retry) {
  if (!root) return;
  let el = root.querySelector(':scope > .net-fail');
  if (!failed) { if (el) el.remove(); return; }
  if (!el) {
    el = document.createElement('div');
    el.className = 'net-fail';
    el.setAttribute('role', 'alert');
    el.innerHTML = '<span>Could not reach the server.</span><button class="btn sm" type="button">Retry</button>';
    const head = root.querySelector(':scope > .win-head');
    if (head && head.nextSibling) root.insertBefore(el, head.nextSibling); else root.prepend(el);
  }
  el.querySelector('button').onclick = () => { el.classList.add('trying'); Promise.resolve(retry && retry()).finally(() => el.isConnected && el.classList.remove('trying')); };
}
