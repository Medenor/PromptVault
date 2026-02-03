# PromptVault Setup Flow Diagrams

Visual representation of the setup wizard flows and component interactions.

## Main Entry Point

```
┌─────────────────────────────────────────┐
│                                         │
│    python scripts/setup/setup.py        │
│                                         │
└───────────────┬─────────────────────────┘
                │
                ▼
        ┌───────────────┐
        │  CLI Options  │
        └───────┬───────┘
                │
    ┌───────────┼───────────┬────────────┐
    │           │           │            │
    ▼           ▼           ▼            ▼
  --quick   --advanced  --component  Interactive
```

## Interactive Mode Flow

```
┌─────────────────────┐
│  Welcome Screen     │
│  - Overview         │
│  - Features list    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Check Saved State   │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
  Found       Not Found
     │           │
     ▼           │
  Resume?        │
   (Y/N)         │
     │           │
     └─────┬─────┘
           │
           ▼
┌─────────────────────┐
│   Mode Selection    │
│  1. Quick Setup     │
│  2. Advanced Setup  │
│  3. Component Setup │
└──────────┬──────────┘
           │
     ┌─────┼─────┬────────┐
     │     │     │        │
     ▼     ▼     ▼        ▼
   Quick Advanced Component Exit
```

## Quick Setup Flow (6 Steps)

```
START
  │
  ▼
┌────────────────────────────────┐
│ Step 1/6: Generate JWT Keys    │
│ ► Run setup_jwt.py             │
│   - Check if keys exist        │
│   - Generate ES256 key pair    │
│   - Validate keys              │
│   - Set permissions            │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 2/6: Environment Config   │
│ ► Run setup_env.py             │
│   - Use development profile    │
│   - Auto-generate .env         │
│   - SQLite database URL        │
│   - Debug logging enabled      │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 3/6: Setup Database       │
│ ► Run setup_database.py        │
│   - Create SQLite database     │
│   - Run Alembic migrations     │
│   - Verify schema              │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 4/6: Create Admin User    │
│ ► Prompt for credentials       │
│   - Username                   │
│   - Email                      │
│   - Note: Create after deploy  │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 5/6: Deploy Application   │
│ ► Run deploy.py                │
│   - Pre-flight checks          │
│   - Start containers           │
│   - Run migrations             │
│   - Smoke tests                │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 6/6: Success Summary      │
│ ► Show access information      │
│   - Web: http://localhost:8001 │
│   - API: /api                  │
│   - Docs: /docs                │
│   - Admin credentials          │
│   - Useful commands            │
└────────────┬───────────────────┘
             │
             ▼
      ┌──────────────┐
      │   COMPLETE   │
      └──────────────┘
```

## Advanced Setup Flow (6 Steps)

```
START
  │
  ▼
┌────────────────────────────────┐
│ Profile Selection              │
│  ► Development or Production?  │
│    - Development: SQLite       │
│    - Production: PostgreSQL    │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Step 1/6: JWT Configuration    │
│ ► Interactive prompts          │
│   - Generate now? (Y/n)        │
│   - Custom paths?              │
│   - Run setup_jwt.py           │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 2/6: Environment Config   │
│ ► Run setup_env.py interactive │
│   Database Configuration:      │
│   - Type: SQLite/PostgreSQL    │
│   - Host, port, credentials    │
│   Security Configuration:      │
│   - JWT settings               │
│   - Password policy            │
│   - Rate limiting              │
│   Email Configuration:         │
│   - SMTP settings              │
│   - Sender information         │
│   Application Settings:        │
│   - Environment                │
│   - Logging levels             │
│   - Base URL                   │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 3/6: Database Setup       │
│ ► Select database type         │
│   - PostgreSQL (recommended)   │
│   - SQLite (simpler)           │
│ ► Run setup_database.py        │
│   - Create database            │
│   - Setup user (PostgreSQL)    │
│   - Run migrations             │
│   - Verify connectivity        │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 4/6: Admin User Creation  │
│ ► Prompt for credentials       │
│   - Username                   │
│   - Email                      │
│   - Instructions for later     │
└────────────┬───────────────────┘
             │
             ▼ [SUCCESS]
             │
┌────────────────────────────────┐
│ Step 5/6: Deployment Config    │
│ ► Review configuration         │
│   - Profile: dev/prod          │
│   - Database type              │
│   - Confirm deployment         │
└────────────┬───────────────────┘
             │
      ┌──────┴──────┐
      │             │
    Deploy      Postpone
      │             │
      ▼             │
┌────────────┐      │
│ Step 6/6:  │      │
│ Deploy App │      │
│            │      │
│ ► deploy.py│      │
└─────┬──────┘      │
      │             │
      └──────┬──────┘
             │
             ▼
      ┌──────────────┐
      │   COMPLETE   │
      └──────────────┘
```

## Component Setup Flow

```
START
  │
  ▼
┌────────────────────────────────┐
│   Component Selection Menu     │
│                                │
│   1. JWT Keys                  │
│   2. Environment               │
│   3. Database                  │
│   4. Deploy                    │
│   5. Exit                      │
└────────────┬───────────────────┘
             │
     ┌───────┼───────┬──────┬─────┐
     │       │       │      │     │
     ▼       ▼       ▼      ▼     ▼
  ┌────┐ ┌────┐ ┌─────┐ ┌────┐ Exit
  │JWT │ │ENV │ │ DB  │ │DPLY│
  └──┬─┘ └──┬─┘ └──┬──┘ └──┬─┘
     │      │      │       │
     ▼      ▼      ▼       ▼
  setup_ setup_ setup_ deploy.py
  jwt.py env.py db.py
     │      │      │       │
     └──────┴──────┴───────┘
             │
             ▼
      ┌──────────────┐
      │   COMPLETE   │
      └──────────────┘
```

## Component Orchestration

```
┌──────────────────────────────────────────────┐
│           SetupWizard (setup.py)             │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │         State Management              │ │
│  │  - .setup_state.json                   │ │
│  │  - Track completed steps               │ │
│  │  - Resume support                      │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │      Component Orchestration           │ │
│  └────────────────────────────────────────┘ │
│           │        │        │        │       │
└───────────┼────────┼────────┼────────┼───────┘
            │        │        │        │
            ▼        ▼        ▼        ▼
      ┌─────────┐ ┌──────┐ ┌────┐ ┌────────┐
      │setup_jwt│ │setup_│ │setup│ │deploy  │
      │   .py   │ │env.py│ │_db │ │  .py   │
      └────┬────┘ └───┬──┘ └──┬─┘ └───┬────┘
           │          │       │       │
           ▼          ▼       ▼       ▼
      ┌─────────────────────────────────┐
      │      Utility Modules            │
      │  - console.py (UI)              │
      │  - validators.py (validation)   │
      │  - config_parser.py (config)    │
      │  - docker_utils.py (Docker)     │
      └─────────────────────────────────┘
```

## Error Handling Flow

```
    Component Execution
           │
           ▼
    ┌──────────────┐
    │  subprocess  │
    │     .run()   │
    └──────┬───────┘
           │
     ┌─────┴─────┐
     │           │
  Success      Error
     │           │
     ▼           ▼
  Return 0   Return 1
     │           │
     ▼           ▼
  Continue   ┌────────────┐
     │       │ Save State │
     │       └─────┬──────┘
     │             │
     │             ▼
     │       ┌────────────┐
     │       │Show Error  │
     │       └─────┬──────┘
     │             │
     │             ▼
     │       ┌────────────┐
     │       │  Stop      │
     │       │  Wizard    │
     │       └─────┬──────┘
     │             │
     │             ▼
     │       User can resume
     │       with:
     └───────► setup.py (again)
```

## Resume Flow

```
┌────────────────────┐
│  Start Wizard      │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Check for          │
│ .setup_state.json  │
└─────────┬──────────┘
          │
    ┌─────┴─────┐
    │           │
  Found     Not Found
    │           │
    ▼           ▼
┌────────┐  ┌────────┐
│ Load   │  │ Fresh  │
│ State  │  │ Start  │
└───┬────┘  └───┬────┘
    │           │
    ▼           │
┌────────┐      │
│Resume? │      │
│ (Y/N)  │      │
└───┬────┘      │
    │           │
  ┌─┴─┐         │
  Y   N         │
  │   │         │
  │   └────┬────┘
  │        │
  ▼        ▼
Resume   Fresh
State    Start
  │        │
  │        │
  ▼        ▼
Skip       Run
Completed  All
Steps      Steps
  │        │
  └────┬───┘
       │
       ▼
   Continue
   Wizard
```

## State File Structure

```json
{
  "completed_steps": [
    "jwt",      // JWT keys generated
    "env",      // Environment configured
    "database", // Database setup complete
    "admin",    // Admin user prompted
    "deploy"    // Application deployed
  ],
  "mode": "quick",           // or "advanced", "component"
  "profile": "development",  // or "production"
  "config": {
    // User choices
  },
  "last_updated": "2024-02-03T14:30:00"
}
```

## Component Dependencies

```
         JWT Keys
            │
            ▼
      Environment ────┐
            │         │
            ▼         ▼
        Database   Deploy
            │         │
            └────┬────┘
                 │
                 ▼
              Admin User
```

## Non-Interactive Mode Flow

```
    CLI with --non-interactive
           │
           ▼
    ┌──────────────┐
    │ Load Defaults│
    │ No Prompts   │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ Run All Steps│
    │ Sequentially │
    └──────┬───────┘
           │
      ┌────┼────┬────┬────┐
      │    │    │    │    │
      ▼    ▼    ▼    ▼    ▼
    JWT  ENV  DB  ADMIN DEPLOY
      │    │    │    │    │
      └────┴────┴────┴────┘
           │
     ┌─────┴─────┐
     │           │
  Success      Error
     │           │
     ▼           ▼
  Exit 0      Exit 1
```

## Configuration File Flow

```
   --config config.yaml
           │
           ▼
    ┌──────────────┐
    │  Load YAML   │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │Select Profile│
    │ - development│
    │ - production │
    │ - staging    │
    │ - docker     │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │Parse Settings│
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │Apply to Steps│
    └──────┬───────┘
           │
           ▼
    Run Setup Flow
```

## CLI Entry Points

```
                setup.py
                   │
     ┌─────────────┼─────────────┬──────────────┐
     │             │             │              │
     ▼             ▼             ▼              ▼
  --quick      --advanced   --component   (interactive)
     │             │             │              │
     ▼             ▼             ▼              ▼
Quick Setup   Advanced     Component       Menu
   Flow         Setup         Menu         Selection
                 Flow
```

## Success Summary Display

```
┌═══════════════════════════════════════════════════════┐
║                                                       ║
║            Setup Completed Successfully!             ║
║                                                       ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Access Your PromptVault Instance:                   ║
║                                                       ║
║  • Web Interface:  http://localhost:8001             ║
║  • API Endpoint:   http://localhost:8001/api         ║
║  • API Docs:       http://localhost:8001/docs        ║
║                                                       ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Admin Credentials:                                  ║
║                                                       ║
║  • Username: admin                                   ║
║  • Email:    admin@example.com                       ║
║                                                       ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Useful Commands:                                    ║
║                                                       ║
║  • View logs:        docker-compose logs -f          ║
║  • Stop services:    docker-compose down             ║
║  • Restart services: docker-compose restart          ║
║  • Check status:     docker-compose ps               ║
║                                                       ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Next Steps:                                         ║
║                                                       ║
║  1. Open http://localhost:8001 in your browser       ║
║  2. Create admin user: python scripts/create_admin   ║
║  3. Log in with your credentials                     ║
║  4. Start organizing your prompts!                   ║
║                                                       ║
└═══════════════════════════════════════════════════════┘
```

## Legend

```
┌────────┐
│  Box   │  = Process/Step
└────────┘

    │
    ▼       = Flow direction

  ┌───┐
  │   │     = Decision point
  └─┬─┘

  ► text    = Action/Command

  [SUCCESS] = Success condition

  (Y/N)     = User prompt
```
