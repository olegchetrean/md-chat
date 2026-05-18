# MD-Chat Android — extra R8/ProGuard keep rules layered on top of upstream
# rules. Required because R8 full-mode strips UniFFI native bindings, breaking
# matrix-rust-sdk at runtime with UnsatisfiedLinkError.

# matrix-rust-sdk UniFFI bindings
-keep class uniffi.** { *; }
-keep class org.matrix.rustcomponents.sdk.** { *; }

# UnifiedPush
-keep class org.unifiedpush.android.** { *; }
-keepattributes *Annotation*

# PostHog
-keep class com.posthog.** { *; }

# Sentry
-keep class io.sentry.** { *; }
-keepattributes Signature, InnerClasses, EnclosingMethod

# Compose (defensive — upstream usually covers this)
-dontwarn androidx.compose.**
