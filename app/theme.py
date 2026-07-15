"""
Theme loader.

This is the only module allowed to read theme.css and push it into the
page. Pages and components never inject their own <style> blocks — if a
new visual need comes up, the token or class goes into theme.css, not
into a one-off st.markdown call somewhere in a page file.
"""

import streamlit as st

from config.settings import settings


@st.cache_data(show_spinner=False)
def _read_css(path_str: str, mtime: float) -> str:
    """Read the stylesheet from disk. Cached by path and file modification time."""
    with open(path_str, "r", encoding="utf-8") as css_file:
        return css_file.read()


@st.cache_data(show_spinner=False)
def get_compiled_theme_css(theme_mode: str, light_mtime: float, dark_mtime: float) -> str:
    """Return the combined CSS block for the specified theme mode, cached by mtime."""
    css = _read_css(str(settings.paths.theme_css), light_mtime)
    if theme_mode == "dark" and settings.paths.theme_dark_css.exists():
        dark_css = _read_css(str(settings.paths.theme_dark_css), dark_mtime)
        css = f"{css}\n\n/* === DARK THEME OVERRIDES === */\n{dark_css}"
    return css


def apply_theme() -> None:
    """Inject the design-system stylesheet into the current Streamlit page."""
    theme_mode = st.session_state.get(settings.session_keys.theme_mode, "light")
    light_mtime = settings.paths.theme_css.stat().st_mtime if settings.paths.theme_css.exists() else 0.0
    dark_mtime = settings.paths.theme_dark_css.stat().st_mtime if settings.paths.theme_dark_css.exists() else 0.0
    css = get_compiled_theme_css(theme_mode, light_mtime, dark_mtime)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # In dark mode inject a JS MutationObserver that patches Baseweb portal popover
    # elements the moment they appear in the DOM. CSS alone cannot beat Baseweb's own
    # inline-style overrides on these dynamically-created portal nodes.
    if theme_mode == "dark":
        import streamlit.components.v1 as components
        components.html(
            """
            <script>
            (function() {
                var BG   = '#131C24';
                var TEXT = '#F0F4F8';
                var BDR  = '#263544';
                var HBG  = '#1D549B';
                var HTXT = '#FFFFFF';

                function paintDark(el) {
                    if (!el || !el.style) return;
                    // skip the main Streamlit iframe wrapper
                    if (el.tagName === 'HTML' || el.tagName === 'BODY') return;

                    var role = (el.getAttribute && el.getAttribute('role')) || '';
                    var baseweb = (el.getAttribute && el.getAttribute('data-baseweb')) || '';
                    var tag = el.tagName || '';

                    // Popover container, menu, listbox, option rows
                    if (
                        baseweb === 'popover' ||
                        baseweb === 'menu' ||
                        baseweb === 'layer' ||
                        role === 'listbox' ||
                        role === 'option' ||
                        role === 'combobox'
                    ) {
                        el.style.setProperty('background', BG, 'important');
                        el.style.setProperty('background-color', BG, 'important');
                        el.style.setProperty('color', TEXT, 'important');
                        el.style.setProperty('-webkit-text-fill-color', TEXT, 'important');
                        el.style.setProperty('border-color', BDR, 'important');
                        el.style.setProperty('border-radius', '0px', 'important');

                        // Paint all children too
                        var kids = el.querySelectorAll('*');
                        for (var i = 0; i < kids.length; i++) {
                            kids[i].style.setProperty('background', BG, 'important');
                            kids[i].style.setProperty('background-color', BG, 'important');
                            kids[i].style.setProperty('color', TEXT, 'important');
                            kids[i].style.setProperty('-webkit-text-fill-color', TEXT, 'important');
                            kids[i].style.setProperty('border-color', BDR, 'important');
                            kids[i].style.setProperty('border-radius', '0px', 'important');
                        }
                    }

                    // Hover state for option rows — attach via mouseover/out
                    if (role === 'option') {
                        el.addEventListener('mouseover', function() {
                            this.style.setProperty('background', HBG, 'important');
                            this.style.setProperty('background-color', HBG, 'important');
                            this.style.setProperty('color', HTXT, 'important');
                            this.style.setProperty('-webkit-text-fill-color', HTXT, 'important');
                        });
                        el.addEventListener('mouseout', function() {
                            this.style.setProperty('background', BG, 'important');
                            this.style.setProperty('background-color', BG, 'important');
                            this.style.setProperty('color', TEXT, 'important');
                            this.style.setProperty('-webkit-text-fill-color', TEXT, 'important');
                        });
                    }
                }

                function walkAndPaint(root) {
                    paintDark(root);
                    if (root.querySelectorAll) {
                        var all = root.querySelectorAll(
                            '[data-baseweb="popover"], [data-baseweb="menu"], ' +
                            '[data-baseweb="layer"], [role="listbox"], ' +
                            '[role="option"], [role="combobox"]'
                        );
                        for (var i = 0; i < all.length; i++) paintDark(all[i]);
                    }
                }

                // Watch the parent window document (not just this iframe)
                var targetDoc = window.parent ? window.parent.document : document;

                var observer = new MutationObserver(function(mutations) {
                    for (var m = 0; m < mutations.length; m++) {
                        var added = mutations[m].addedNodes;
                        for (var n = 0; n < added.length; n++) {
                            walkAndPaint(added[n]);
                        }
                        // Also re-paint changed attributes (e.g. style attr changes)
                        if (mutations[m].type === 'attributes') {
                            walkAndPaint(mutations[m].target);
                        }
                    }
                });

                observer.observe(targetDoc.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ['style', 'class']
                });

                // Run once immediately to catch anything already in the DOM
                walkAndPaint(targetDoc.body);
            })();
            </script>
            """,
            height=0,
        )

