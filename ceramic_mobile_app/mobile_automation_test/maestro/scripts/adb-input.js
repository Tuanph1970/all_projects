// Fast text input for Maestro using built-in capabilities
// Note: Maestro's GraalJS doesn't support Node.js require()

// Get the text from environment
var text = TEXT || '';

// Unfortunately, Maestro's JS runtime cannot execute shell commands directly
// This script just passes through - the actual fast input needs a different approach

// Set output for Maestro
output.text = text;
output.result = 'prepared';
