// Fast text input using ADB clipboard (much faster than character-by-character)
// This sets clipboard and sends paste command

const { execSync } = require('child_process');

const fieldId = process.env.FIELD_ID;
const text = process.env.TEXT;

// Set clipboard content via ADB
execSync(`adb shell am broadcast -a clipper.set -e text "${text}"`, { encoding: 'utf8' });

// Or use input text directly (faster than Maestro's inputText)
// execSync(`adb shell input text "${text.replace(/ /g, '%s')}"`, { encoding: 'utf8' });

// Send paste command (Ctrl+V)
execSync('adb shell input keyevent 279', { encoding: 'utf8' });  // KEYCODE_PASTE

output.result = 'success';
