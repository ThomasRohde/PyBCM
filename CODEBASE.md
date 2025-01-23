# Codebase Documentation

## Session Management

The application uses a combination of HTTP sessions and WebSocket connections to manage user state:

### Server-side (`bcm/api/server.py`)
- User sessions are stored in memory using the `active_users` dictionary
- Each session contains:
  - session_id: Unique identifier
  - nickname: User's display name
  - locked_capabilities: List of capability IDs locked by the user
- The ConnectionManager tracks WebSocket connections and maps them to sessions
- Automatic cleanup occurs when:
  - Users explicitly logout
  - WebSocket connections are dropped (browser closed)

### Client-side
- Session management in `bcm-client/src/contexts/AppContext.tsx`
- WebSocket connection handling in `bcm-client/src/api/client.ts`
- Sessions are established on login and include:
  - WebSocket connection with session ID
  - User information
  - Capability locks

## Capability Locking System

The application implements a distributed locking system for capabilities:
- Users can lock capabilities for editing
- Locks are automatically cleared when:
  - Users explicitly unlock capabilities
  - Users logout
  - Browser connections are lost
- Lock inheritance prevents editing of parent capabilities when children are locked

## API Structure

The server exposes two main types of endpoints:
1. HTTP REST API endpoints for:
   - User session management
   - Capability CRUD operations
   - Settings management
   - Layout and formatting operations

2. WebSocket endpoint for:
   - Real-time updates
   - User presence
   - Model change notifications
   - Session management
