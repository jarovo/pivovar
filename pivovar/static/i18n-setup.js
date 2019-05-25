const messages = {
  en: {
    brewery: "Brewery",
    "water temp in time": 'Water temp in time.',
  },
  cs: {
    brewery: "Pivovar",
    "Phases": "Fáze",
    "Keg Washer": 'Myčka sudů: {wm_name}',
    "water temp in time": 'Teplota vody v čase.',
    "Wash machines": "Myčky",
    "Fermenters": "Spilky",
  }
}

function guessI18nLanguage() {
    return navigator.languages ? navigator.languages[0]
            : (navigator.language || navigator.userLanguage)
}

// Create VueI18n instance with options
const i18n = new VueI18n({
  locale: guessI18nLanguage(),
  fallbackLocale: 'en',
  messages, // set locale messages
})

function setI18nLanguage(lang) {
  i18n.locale = lang
  document.querySelector('html').setAttribute('lang', lang)
  return lang
}

setI18nLanguage(guessI18nLanguage())
