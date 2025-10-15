/*
 * Shortcut Sage Event Monitor - KWin Script
 * Monitors KDE Plasma events and sends them to Shortcut Sage daemon
 */

// Configuration
const DAEMON_SERVICE = "org.shortcutsage.Daemon";
const DAEMON_PATH = "/org/shortcutsage/Daemon";

// Initialize DBus interface
function initDBus() {
    try {
        var dbusInterface = workspace.knownInterfaces[DAEMON_SERVICE];
        if (dbusInterface) {
            print("Found Shortcut Sage daemon interface");
            return true;
        } else {
            print("Shortcut Sage daemon not available");
            return false;
        }
    } catch (error) {
        print("Failed to connect to Shortcut Sage daemon: " + error);
        return false;
    }
}

// Function to send event to daemon via DBus
function sendEvent(type, action, metadata) {
    // Using DBus to call the daemon's SendEvent method
    callDBus(
        DAEMON_SERVICE,
        DAEMON_PATH,
        DAEMON_SERVICE,
        "SendEvent",
        JSON.stringify({
            timestamp: new Date().toISOString(),
            type: type,
            action: action,
            metadata: metadata || {}
        })
    );
}

// Monitor workspace events
function setupEventListeners() {
    // Desktop switch events
    workspace.clientDesktopChanged.connect(function(client, desktop) {
        sendEvent("desktop_switch", "switch_desktop", { 
            window: client ? client.caption : "unknown",
            desktop: desktop
        });
    });

    // Window focus events
    workspace.clientActivated.connect(function(client) {
        if (client) {
            sendEvent("window_focus", "window_focus", {
                window: client.caption,
                app: client.resourceClass ? client.resourceClass.toString() : "unknown"
            });
        }
    });

    // Screen edge activation (overview, etc.)
    workspace.screenEdgeActivated.connect(function(edge, desktop) {
        var action = "unknown";
        if (edge === 0) action = "overview";  // Top edge usually shows overview
        else if (edge === 2) action = "application_launcher";  // Bottom edge
        else action = "screen_edge";
        
        sendEvent("desktop_state", action, {
            edge: edge,
            desktop: desktop
        });
    });

    // Window geometry changes (for tiling, maximizing, etc.)
    workspace.clientStepUserMovedResized.connect(function(client, step) {
        if (client && step) {
            var action = "window_move";
            if (client.maximizedHorizontally && client.maximizedVertically) {
                action = "maximize";
            } else if (!client.maximizedHorizontally && !client.maximizedVertically) {
                action = "window_move";
            }
            
            sendEvent("window_state", action, {
                window: client.caption,
                maximized: client.maximizedHorizontally && client.maximizedVertically
            });
        }
    });
}

// Register a test shortcut for development
function setupTestShortcut() {
    registerShortcut(
        "Shortcut Sage Test", 
        "Test shortcut for Shortcut Sage development", 
        "Ctrl+Alt+S", 
        function() {
            sendEvent("test", "test_shortcut", { 
                source: "kwin_script"
            });
        }
    );
}

// Initialize when script loads
function init() {
    print("Shortcut Sage KWin script initializing...");
    
    if (initDBus()) {
        setupEventListeners();
        setupTestShortcut();
        print("Shortcut Sage KWin script initialized successfully");
    } else {
        print("Shortcut Sage KWin script initialized in fallback mode - daemon not available");
        // Still set up events but with fallback behavior if needed
        setupTestShortcut();
    }
}

// Run initialization
init();