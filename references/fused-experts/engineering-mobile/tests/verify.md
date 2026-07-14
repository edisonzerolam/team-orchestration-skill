# Verify: engineering-mobile

## must-pass

| # | Scenario | Input | Expected Mode |
|---|---------|-------|---------------|
| 1 | Native iOS UI | "Build a SwiftUI product list view" | mobile-native |
| 2 | Cross-platform app | "Design a React Native chat screen" | mobile-cross |
| 3 | Release pipeline | "Set up fastlane for iOS deployment" | mobile-release |
| 4 | Desktop app | "Build an Electron tray app" | desktop |
| 5 | App store submission | "How to submit to App Store" | mobile-release |

## should-pass (>=2)

| # | Scenario | Expected |
|---|---------|----------|
| 6 | Cross-platform should mention platform-specific code | Correct scope |
| 7 | Release discussion should mention phased rollouts | Correct scope |

## must-not-fail

| # | Check |
|---|-------|
| 8 | Lost signing/certificate knowledge from mobile-release-engineer |
| 9 | Lost IPC security rules from desktop-app-engineer |
