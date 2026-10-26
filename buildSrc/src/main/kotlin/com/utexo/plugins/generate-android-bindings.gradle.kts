package com.utexo.plugins

import org.gradle.kotlin.dsl.register

val llvmArchPath = when (operatingSystem) {
    OS.MAC   -> "darwin-x86_64"
    OS.LINUX -> "linux-x86_64"
    OS.OTHER -> throw Error("Cannot build Android library from current architecture")
}

val androidPath = "${project.projectDir}/../android"
val rgbLibUniffiPath = "${project.projectDir}/../rgb-lib/bindings/uniffi"

val jniLibsDir = "$androidPath/src/main/jniLibs/"

val androidNdkRoot = System.getenv("ANDROID_NDK_ROOT")
    ?: "${System.getenv("ANDROID_SDK_ROOT")}/ndk-bundle"
val llvmPath = "$androidNdkRoot/toolchains/llvm/prebuilt/$llvmArchPath"

val cargoBuildCommonArgs: MutableList<String> = mutableListOf("build", "--locked", "--release", "--target")

val prepareBuild by tasks.register("prepareBuild") {
    doLast {
        File(jniLibsDir).deleteRecursively()
        // This directory contains only generated bindings. Remove old package paths too.
        File("$androidPath/src/main/kotlin").deleteRecursively()
    }
}

// arm64-v8a is the most popular hardware architecture for Android
val buildAndroidAarch64Binary by tasks.register<Exec>("buildAndroidAarch64Binary") {
    dependsOn(prepareBuild)

    workingDir(rgbLibUniffiPath)
    val cargoArgs = cargoBuildCommonArgs + mutableListOf("aarch64-linux-android")

    executable("cargo")
    args(cargoArgs)

    // if ANDROID_NDK_ROOT is not set then set it to github actions default
    if (System.getenv("ANDROID_NDK_ROOT") == null) {
        environment(
            Pair("ANDROID_NDK_ROOT", "${System.getenv("ANDROID_SDK_ROOT")}/ndk-bundle")
        )
    }

    environment(
        // add build toolchain to PATH
        Pair("PATH", "$llvmPath/bin:${System.getenv("PATH")}"),

        Pair("CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER", "aarch64-linux-android21-clang"),
        Pair("CC_aarch64_linux_android", "aarch64-linux-android21-clang"),
        Pair("CXX_aarch64_linux_android", "aarch64-linux-android21-clang++"),
        Pair("AR_aarch64_linux_android", "llvm-ar"),
        Pair("RANLIB_aarch64_linux_android", "llvm-ranlib"),

        // bindgen uses libclang separately from CC and needs Android headers explicitly.
        Pair("BINDGEN_EXTRA_CLANG_ARGS_aarch64_linux_android",
            "--target=aarch64-linux-android21 --sysroot=\"$llvmPath/sysroot\" " +
                "-isystem \"$llvmPath/sysroot/usr/include/aarch64-linux-android\""),

        // support 16KB pages
        Pair("RUSTFLAGS", "-C link-arg=-Wl,-z,max-page-size=16384"),
    )

    doLast {
        println("Native library for rgb-lib-android on aarch64 built successfully")
    }
}

// the x86_64 version of the library is mostly used by emulators
val buildAndroidX86_64Binary by tasks.register<Exec>("buildAndroidX86_64Binary") {
    dependsOn(buildAndroidAarch64Binary)

    workingDir(rgbLibUniffiPath)
    val cargoArgs = cargoBuildCommonArgs + mutableListOf("x86_64-linux-android")

    executable("cargo")
    args(cargoArgs)

    // if ANDROID_NDK_ROOT is not set then set it to github actions default
    if (System.getenv("ANDROID_NDK_ROOT") == null) {
        environment(
            Pair("ANDROID_NDK_ROOT", "${System.getenv("ANDROID_SDK_ROOT")}/ndk-bundle")
        )
    }

    environment(
        // add build toolchain to PATH
        Pair("PATH", "$llvmPath/bin:${System.getenv("PATH")}"),

        Pair("CARGO_TARGET_X86_64_LINUX_ANDROID_LINKER", "x86_64-linux-android21-clang"),
        Pair("CC_x86_64_linux_android", "x86_64-linux-android21-clang"),
        Pair("CXX_x86_64_linux_android", "x86_64-linux-android21-clang++"),
        Pair("AR_x86_64_linux_android", "llvm-ar"),
        Pair("RANLIB_x86_64_linux_android", "llvm-ranlib"),

        // Keep these arguments target-specific so host UniFFI generation uses host headers.
        Pair("BINDGEN_EXTRA_CLANG_ARGS_x86_64_linux_android",
            "--target=x86_64-linux-android21 --sysroot=\"$llvmPath/sysroot\" " +
                "-isystem \"$llvmPath/sysroot/usr/include/x86_64-linux-android\""),

        // support 16KB pages
        Pair("RUSTFLAGS", "-C link-arg=-Wl,-z,max-page-size=16384"),
    )

    doLast {
        println("Native library for rgb-lib-android on x86_64 built successfully")
    }
}

// move the native libs build by cargo from rgb-lib/bindings/uniffi/target/<architecture>/release/
// to their place in the rgb-lib-android library
// the task only copies the available binaries built using the buildAndroid<architecture>Binary tasks
val moveNativeAndroidLibs by tasks.register<Copy>("moveNativeAndroidLibs") {
    dependsOn(buildAndroidAarch64Binary, buildAndroidX86_64Binary)

    into(jniLibsDir)

    into("arm64-v8a") {
        from("$rgbLibUniffiPath/target/aarch64-linux-android/release/librgblibuniffi.so")
    }

    into("x86_64") {
        from("$rgbLibUniffiPath/target/x86_64-linux-android/release/librgblibuniffi.so")
    }

    doLast {
        println("Native binaries for Android moved to ./android/src/main/jniLibs/")
    }
}

// generate the bindings using the rgb-lib-uniffi-bindgen tool located in the rgb-lib submodule
val generateAndroidBindings by tasks.register<Exec>("generateAndroidBindings") {
    dependsOn(moveNativeAndroidLibs)

    workingDir(rgbLibUniffiPath)
    executable("cargo")
    args("run", "--locked", "--bin", "rgb-lib-uniffi-bindgen", "generate", "src/rgb-lib.udl",
        "--language", "kotlin", "--out-dir", "$androidPath/src/main/kotlin",
        "--config", providers.gradleProperty("uniffiConfig").getOrElse("uniffi.toml"))

    doLast {
        println("Android bindings file successfully created")
    }
}

tasks.matching { it.name == "preBuild" || it.name.endsWith("SourcesJar") }.configureEach {
    dependsOn(generateAndroidBindings)
}

// create an aggregate task which will run the required tasks to build the Android libs in order
// the task will also appear in the printout of the ./gradlew tasks task with group and description
tasks.register("buildAndroidLib") {
    group = "Utexo"
    description = "Aggregate task to build Android library"

    dependsOn(
        prepareBuild,
        buildAndroidAarch64Binary,
        buildAndroidX86_64Binary,
        moveNativeAndroidLibs,
        generateAndroidBindings
    )
}
