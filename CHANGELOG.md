# Changelog

## [Unreleased]

### Added
- Automatic cleanup of user sessions and capability locks when browsers are closed unexpectedly
- Session tracking in WebSocket connections for better connection management
- Improved error handling for WebSocket disconnections

### Changed
- Modified WebSocket connection to include session ID for proper session management
- Enhanced ConnectionManager to track session-websocket mappings
- Updated client-side WebSocket connection logic to support session-based connections

### Fixed
- Issue with orphaned locks when users close their browsers without logging out
- Improved session cleanup on unexpected disconnections
