// Fast text input using shell command via http request to a local helper
// Or use Maestro's built-in capabilities

var text = TEXT || '';

// For Maestro, we'll use a workaround - set the text in output
// and use a separate mechanism for ADB input
output.inputText = text;
output.result = 'text_ready';

// Try using GraalJS polyglot if available
try {
    var ProcessBuilder = Java.type('java.lang.ProcessBuilder');
    var pb = new ProcessBuilder('adb', 'shell', 'input', 'text', text.replace(/ /g, '%s'));
    var process = pb.start();
    process.waitFor();
    output.result = 'completed_java';
} catch (e) {
    // Java not available, output text for manual handling
    output.error = e.toString();
    output.result = 'java_unavailable';
}
