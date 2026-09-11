# SpellScroll ProGuard / R8 Optimization Rules

# Keep JavascriptInterface methods accessible to WebView JavaScript
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Keep WebChromeClient and WebViewClient subclasses and public methods
-keepclassmembers class * extends android.webkit.WebViewClient {
    public *;
}

-keepclassmembers class * extends android.webkit.WebChromeClient {
    public *;
}

# Don't obfuscate JavaScript bridge class
-keep class com.spellscroll.app.SpellScrollNativeBridge { *; }

# Keep data models for Gson serialization
-keep class com.spellscroll.app.model.** { *; }
-keepattributes Signature
-keepattributes *Annotation*

# OkHttp & Coil
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn coil.**

# Allow optimization and shrinking
-optimizationpasses 5
-dontusemixedcaseclassnames
-dontskipnonpubliclibraryclasses
-verbose
