# RGB Lib Kotlin bindings

This project builds an Android library, `rgb-lib-android`, for the [rgb-lib]
Rust library, which is included as a git submodule. The bindings are created by
the [rgb-lib-uniffi] project, which is located inside the rgb-lib submodule.

## Usage

To use the Kotlin library add the following to your project gradle dependencies:

```groovy
repositories {
    mavenCentral()
}

dependencies {
    implementation 'com.utexo:rgb-lib-android:<version>'
}
```

## Contributing

Clone the project, including submodules:

```bash
git clone git@github.com:UTEXO-Protocol/rgb-lib-kotlin.git --recurse-submodules
```

When fetching updates, remember to update the submodule as well:

```bash
git submodule update --init
```

### Build

#### In docker

Build the docker image (if your user or group IDs are not `1000`, adjust the
environment variables `MYUID` and `MYGID` in the `compose.yaml` file
accordingly):

```bash
docker compose run --build --rm builder
```

Notes:

- image build takes a long time and uses a lot of disk space
- the local directory will be mounted into the container at runtime
- the `gradle_cache` local directory will be mounted into the container to
  cache gradle downloads

#### Local

Setup the following environment variables:

- `ANDROID_SDK_ROOT` (e.g. `export ANDROID_SDK_ROOT=$HOME/Android/Sdk`)
- `ANDROID_NDK_ROOT` (`export ANDROID_NDK_ROOT=$ANDROID_SDK_ROOT/ndk/25.<NDK_VERSION>`)

Note: NDK version 25.2.x can be installed via android studio (SDK Manager) or
command-line tools (sdkmanager).

Add the required Android rust targets:

```bash
rustup target add aarch64-linux-android
rustup target add x86_64-linux-android
```

Build the Android library:

```bash
./gradlew :android:buildAndroidLib
```

### Page alignment

Check the build library page alignment:

```bash
for LIB in $(find rgb-lib/bindings/uniffi/target/ -wholename '*release/librgblibuniffi.so'); do ls -l "$LIB"; readelf -l "$LIB" |grep -A1 LOAD; done
```

The last column of each LOAD row is the alignment:
- 0x1000 => pages align to 4KB
- 0x4000 => pages align to 16KB

### Publish

Make sure you have OpenJDK 21 available. Running `java --version` should return
`openjdk 21.0.10` or a newer 21.x version. If this is not the case, you can
download [OpenJDK 21], unpack it to a directory of your choice (e.g.
`$HOME/jdk`) and then set the following environment variables accordingly:

- `JAVA_HOME` (e.g. `export JAVA_HOME=$HOME/jdk/jdk-21.0.2`)
- `PATH` (`export PATH=$JAVA_HOME/bin:$PATH`)

Setup the following android environment variables:

- `ANDROID_SDK_ROOT` (e.g. `export ANDROID_SDK_ROOT="$HOME/Android/Sdk"`)
- `ANDROID_HOME` (`export ANDROID_HOME="$ANDROID_SDK_ROOT"`)
- `ANDROID_NDK_ROOT` (`export ANDROID_NDK_ROOT=$ANDROID_SDK_ROOT/ndk/25.2.<NDK_VERSION>`)

#### To local Maven repository

Publish the library to your local Maven repository:

```bash
./gradlew :android:publishToMavenLocal
```

#### To Maven Central repository (project maintainers only)

Create a `~/.jreleaser/config.yml` file with the publishing and signing information:

```yaml
JRELEASER_GITHUB_OWNER: UTEXO-Protocol
JRELEASER_GITHUB_NAME: rgb-lib-kotlin
JRELEASER_GITHUB_TOKEN: fake-token-not-used

JRELEASER_MAVENCENTRAL_USERNAME: "<your-publisher-portal-username>"
JRELEASER_MAVENCENTRAL_PASSWORD: "<your-publisher-portal-password>"
```

Test your configuration by running:
```shell
./gradlew jreleaserConfig
```

Build the artifacts by running:
```shell
./gradlew :android:publish
```

Set your GPG password to the apprpriate environment variable by running:
```shell
read -rsp "GPG password: " JRELEASER_GPG_PASSPHRASE
```

Test the publishing by running:
```shell
./gradlew jreleaserDeploy --dryrun -Pjreleaser.gpg.keyName="<your_key_id>" -Pjreleaser.gpg.passphrase="$JRELEASER_GPG_PASSPHRASE"
```

Publish by running:
```shell
./gradlew jreleaserDeploy -Pjreleaser.gpg.keyName="<your_key_id>" -Pjreleaser.gpg.passphrase="$JRELEASER_GPG_PASSPHRASE"
```

[rgb-lib]: https://github.com/RGB-Tools/rgb-lib
[rgb-lib-uniffi]: https://github.com/RGB-Tools/rgb-lib/tree/master/bindings/uniffi
[OpenJDK 21]: (https://jdk.java.net/archive/)

## BFA releases

The separate `BFA Android Release` workflow builds **rgb-lib-bfa**, while the
existing `Build and Release` workflow continues to publish ordinary rgb-lib.
BFA uses `com.utexo:rgb-lib-bfa-android:<version>` and Kotlin package `com.utexo`.
Do not include both rgb-lib variants in one application: their classes and native
library names overlap.

A source release `v0.3.0-beta.7` produces package version `0.3.0-beta.7-bfa`.
Both mobile workflows must receive that version and the **same full source SHA**.
The source checkout uses `BFA_SOURCE_READ_TOKEN` (read-only Contents access to
`UTEXO-Protocol/rgb-lib-bfa`); no private Rust sources are uploaded.

### Test and publish

1. Merge the workflow into the repository's default branch so that GitHub can
   receive `repository_dispatch` events. For a first test, select the feature
   branch when running the workflow manually once GitHub has registered it.
2. Set `BFA_SOURCE_READ_TOKEN`. Run `BFA Android Release` with `version`,
   `source_sha`, and `publish=false` (the default). The Actions artifact contains
   the AAR, Maven staging directory, `version.json`, and `SHA256SUMS`.
3. Configure the existing Maven/GPG secrets: `MAVENCENTRAL_USERNAME`,
   `MAVENCENTRAL_PASSWORD`, `GPG_SECRET_KEY`, `GPG_KEY_NAME`,
   `GPG_PASSPHRASE`. The `com.utexo` namespace must be authorized in Central.
4. Publish using the same version and SHA with `publish=true`, or enable the
   dispatch integration in rgb-lib-bfa after **both** platform tests pass.

Published assets are attached to tag `bfa-v<version>` in this **public** repository.
Actions artifacts alone are temporary and are not the public distribution channel.
The release AAR is checked byte-for-byte against the staged Maven AAR. It contains
`arm64-v8a` and `x86_64` libraries, generated Kotlin code, and
`assets/rgb-lib-bfa-version.json`. Minimum Android API: 21. The BFA build pins
Rust 1.94.1 and NDK 28.2.13676358 and uses the committed Cargo lockfile.

```groovy
dependencies {
    implementation 'com.utexo:rgb-lib-bfa-android:0.3.0-beta.7-bfa'
}
```

The version above illustrates the naming convention; it is not a claim that the
release already exists. For direct AAR integration, also provide the dependencies
listed in the published Maven POM (including the Android JNA AAR).

Download `SHA256SUMS`, `version.json`, and the AAR into one directory and run
`sha256sum --check SHA256SUMS`. Compare `source_commit` with the iOS release's
`version.json` before integrating both into rgb-sdk-rn.

Publishing refuses an existing GitHub release tag. Maven Central versions are
immutable. If Maven succeeds but GitHub publication fails, recover the GitHub
release from the retained build artifact instead of attempting to replace the
Maven version. A new source commit requires a new package version on both platforms.
