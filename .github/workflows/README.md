# Workflows

## release.yml — Build and Release

Builds Android library, publishes to Maven Central, and creates a GitHub Release.

- **Trigger**: automatically via `repository_dispatch` from `rgb-lib`, or manually
- **Input**: `version` (e.g. `0.3.0-beta.5`, no `v` prefix)
- **What it does**:
  1. Checks out `utexo-master` with rgb-lib submodule
  2. Builds the Android library (arm64 + x86_64) via Gradle
  3. Signs and publishes to Maven Central via JReleaser
  4. Creates a GitHub Release with the AAR artifact

## test.yml — Test Library (local)

Tests the Kotlin/Android bindings using a **locally built** library.

- **Trigger**: push to `utexo-master`, PRs to `utexo-master`, after release workflow, or manually
- **What it does**:
  1. Builds the Android library from source with Rust cross-compilation
  2. Runs unit tests via `./gradlew :android:test`
  3. Runs instrumented tests on Android emulator (API 34, x86_64)

## test_tag.yml — Test Library (published tag)

Tests the **published** Maven Central artifact — simulates what end users do.

- **Trigger**: push of a `v*` tag (i.e. right after a release)
- **What it does**:
  1. Strips `v` prefix to get the Maven Central version
  2. Replaces local project dependency with `com.utexo:rgb-lib-android:<version>` from Maven Central
  3. Waits for Maven Central to index the artifact (up to ~20 min with retries)
  4. Runs unit and instrumented tests against the published package