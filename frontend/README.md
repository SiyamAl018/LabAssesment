# FarmLog frontend

React + TypeScript + Vite frontend foundation for Sunny's part of LabAssesment.

## Run locally

```sh
cd frontend
npm install
npm run dev
```

Production check: `npm run build`. Preview production output: `npm run preview`.
Requires Node.js 20.19+ or 22.12+.

## Structure

```text
src/
  app/                App and route definitions
  assets/             Local images and icons
  components/
    layout/           Shared sidebar and application layout
    ui/               Shared page headers and empty states
  features/
    visits/           Future speech capture, parsing review, name confirmation
    farms/            Future farm profile and visit timeline logic
    reminders/        Future overdue and upcoming follow-ups
    reports/          Future monthly summaries
  hooks/              Shared React hooks
  pages/              Route-level screens
  services/           Configurable backend client
  styles/             Global styles and responsive layout
  types/              Initial shared data contracts
  utils/              Shared helpers
```

Routes: `/`, `/visits/new`, `/farms`, `/farms/:farmId`, `/reports`.

This step provides navigation, responsive layout, page shells, editable notes,
language/month controls, and an API client. Voice recognition, saving, name matching,
farm data, reminders, and report generation are not implemented yet. Dashes mean
data is not connected, rather than zero records. No backend requests run yet.

Copy `.env.example` to `.env` to configure the API URL. Coordinate endpoint paths
and data contracts with Siyam (backend) and Khalid (database) before integration.
For production hosting, configure SPA fallback to `index.html` for nested routes.

## Voice-to-text

Record Visit now uses Web Speech recognition with Bangla (`bn-BD`) by default
and optional English (`en-US`). Start/stop controls show recognition status,
interim speech, and a final editable transcript. Starting another session appends
to existing text. Permission, network, unsupported browser/language, missing mic,
and no-speech errors are displayed. Leaving the page aborts recognition.

Use HTTPS or localhost and allow microphone permission. Browser speech services
may require internet and send audio to a remote service. Language availability
varies by browser/service. Audio files and visit submissions are not saved yet.
This supersedes the earlier note that voice recognition is not implemented.

Manual check: open /visits/new, allow microphone, speak Bangla, stop, edit text,
restart to append, clear text, and deny microphone access to check the error.
Also check unsupported browsers and navigation away during recognition.
