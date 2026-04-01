# prevent stripping of the JNA library
-keep class com.sun.jna.** { *; }
-keep class net.java.dev.jna.** { *; }

# prevent stripping of Kotlin/Rust bindings
-keep class org.rgbtools.** { *; }

# keep native methods and their structure
-keepclasseswithmembernames class * {
    native <methods>;
}
-keep class * extends com.sun.jna.Structure {
    <fields>;
    public <methods>;
}
