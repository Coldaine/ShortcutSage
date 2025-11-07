/**
 * Shortcut Sage - KWin Event Monitor
 *
 * Monitors desktop events and sends them to the Shortcut Sage daemon via DBus.
 *
 * Events monitored:
 * - Desktop/workspace switches
 * - Window focus changes
 * - Show desktop state changes
 *
 * Dev shortcut: Meta+Shift+S sends a test event
 *
 * Privacy: Window titles are NOT captured by default - only resource classes
 * (application IDs) are sent to maintain user privacy.
 */

// DBus connection to Shortcut Sage daemon
const BUS_NAME = "org.shortcutsage.Daemon";
const OBJECT_PATH = "/org/shortcutsage/Daemon";
const INTERFACE = "org.shortcutsage.Daemon";

// Logging configuration
const DEBUG = false;  // Set to true for verbose logging during development
const LOG_PREFIX = "[ShortcutSage]";

// Helper function for logging
function log(message) {
    if (DEBUG) {
        console.log(LOG_PREFIX + " " + message);
    }
}

function logError(message) {
    console.error(LOG_PREFIX + " ERROR: " + message);
}

// Initialize the script
log("Initializing KWin Event Monitor");

/**
 * Send an event to the daemon via DBus
 * @param {string} type - Event type (e.g., "window_focus", "desktop_switch")
 * @param {string} action - Action name (e.g., "show_desktop", "tile_left")
 * @param {Object} metadata - Additional metadata (optional)
 */
function sendEvent(type, action, metadata) {
    try {
        // Build event object
        const event = {
            timestamp: new Date().toISOString(),
            type: type,
            action: action,
            metadata: metadata || {}
        };

        const eventJson = JSON.stringify(event);
        log("Sending event: " + eventJson);

        // Call DBus method
        callDBus(
            BUS_NAME,
            OBJECT_PATH,
            INTERFACE,
            "SendEvent",
            eventJson
        );
    } catch (error) {
        logError("Failed to send event: " + error);
    }
}

/**
 * Ping the daemon to check if it's alive
 */
function pingDaemon() {
    try {
        const result = callDBus(
            BUS_NAME,
            OBJECT_PATH,
            INTERFACE,
            "Ping"
        );
        log("Ping result: " + result);
        return result === "pong";
    } catch (error) {
        logError("Daemon not responding to ping: " + error);
        return false;
    }
}

// Track previous state to detect changes
// These variables must be mutable (using `let`) because they are updated
// in event handlers to compare with new states
let previousDesktop = workspace.currentDesktop;
let showingDesktop = workspace.showingDesktop;

/**
 * Monitor desktop/workspace switches
 */
workspace.currentDesktopChanged.connect(function(desktop, client) {
    if (desktop !== previousDesktop) {
        log("Desktop switched: " + previousDesktop + " -> " + desktop);
        sendEvent(
            "desktop_switch",
            "switch_desktop",
            {
                from: previousDesktop,
                to: desktop
            }
        );
        previousDesktop = desktop;
    }
});

/**
 * Monitor "Show Desktop" state changes
 */
workspace.showingDesktopChanged.connect(function(showing) {
    if (showing !== showingDesktop) {
        log("Show desktop changed: " + showing);
        const action = showing ? "show_desktop" : "hide_desktop";
        sendEvent(
            "show_desktop",
            action,
            { showing: showing }
        );
        showingDesktop = showing;
    }
});

/**
 * Monitor active window (focus) changes
 */
workspace.clientActivated.connect(function(client) {
    if (client) {
        log("Window activated: " + client.caption);
        sendEvent(
            "window_focus",
            "window_activated",
            {
                // caption: client.caption,  // Uncomment to include window titles (privacy trade-off)
                resourceClass: client.resourceClass || "unknown"
            }
        );
    }
});

/**
 * Dev shortcut: Meta+Shift+S to send a test event
 */
registerShortcut(
    "ShortcutSage: Test Event",
    "ShortcutSage: Send Test Event (Meta+Shift+S)",
    "Meta+Shift+S",
    function() {
        log("Test event triggered");
        sendEvent(
            "test",
            "test_event",
            { source: "dev_shortcut" }
        );
    }
);

// Ping daemon on startup to verify connection
log("Pinging daemon...");
if (pingDaemon()) {
    log("Successfully connected to daemon");
} else {
    logError("Could not connect to daemon - is it running?");
    logError("Start the daemon with: shortcut-sage daemon <config_dir>");
}

log("KWin Event Monitor initialized successfully");
