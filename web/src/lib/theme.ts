export const THEME_KEY = "bazarcito:theme";

/**
 * Runs in <head> before the page paints. Everyone starts on the light theme; the device's own dark setting
 * is not followed, so the site always looks the way it was designed until the visitor picks dark in the
 * header. The choice is remembered in this browser.
 */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");document.documentElement.dataset.theme=t==="dark"?"dark":"light"}catch(e){document.documentElement.dataset.theme="light"}})()`;
