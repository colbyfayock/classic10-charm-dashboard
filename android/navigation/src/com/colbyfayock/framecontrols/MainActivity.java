package com.colbyfayock.framecontrols;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private TextView status;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        int padding = Math.round(20 * getResources().getDisplayMetrics().density);
        content.setPadding(padding, padding, padding, padding);
        TextView title = new TextView(this);
        title.setText("Frame Controls");
        title.setTextSize(24);
        content.addView(title);
        TextView help = new TextView(this);
        help.setText("Back and Home controls for this frame. No network or screen-content access.\n\n"
                + "1. Tap Start controls.\n2. Open Accessibility settings and manually enable Frame Controls.\n"
                + "3. Test Back and Home while ADB remains available.\n\n"
                + "Drag Move to reposition. Hide or Stop controls removes the buttons. "
                + "Turn off the accessibility service in Android settings to revoke access completely.");
        help.setTextSize(17);
        content.addView(help);
        status = new TextView(this);
        status.setTextSize(17);
        content.addView(status);
        addButton(content, "Start controls", new View.OnClickListener() {
            @Override public void onClick(View view) {
                getSharedPreferences(NavigationService.PREFERENCES, MODE_PRIVATE).edit()
                        .putBoolean("enabled", true).remove("last_error").apply();
                NavigationService.refreshConnected();
                updateStatus();
            }
        });
        addButton(content, "Stop controls", new View.OnClickListener() {
            @Override public void onClick(View view) {
                getSharedPreferences(NavigationService.PREFERENCES, MODE_PRIVATE).edit()
                        .putBoolean("enabled", false).apply();
                NavigationService.refreshConnected();
                updateStatus();
            }
        });
        addButton(content, "Open accessibility settings", new View.OnClickListener() {
            @Override public void onClick(View view) {
                open(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
            }
        });
        addButton(content, "Open VPhoto fallback", new View.OnClickListener() {
            @Override public void onClick(View view) {
                open(new Intent().setComponent(new ComponentName(
                        "com.waophoto.smartframe", "com.waophoto.smartframe.ui.SplashActivity")));
            }
        });
        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
    }

    private void addButton(LinearLayout parent, String text, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(text);
        button.setOnClickListener(listener);
        parent.addView(button, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
    }

    private void open(Intent intent) {
        try {
            startActivity(intent);
        } catch (ActivityNotFoundException error) {
            Toast.makeText(this, "That activity is unavailable. Use the verified ADB fallback.", Toast.LENGTH_LONG).show();
        } catch (SecurityException error) {
            Toast.makeText(this, "Android blocked this activity. Use the verified ADB fallback.", Toast.LENGTH_LONG).show();
        }
    }

    private void updateStatus() {
        boolean enabled = getSharedPreferences(NavigationService.PREFERENCES, MODE_PRIVATE)
                .getBoolean("enabled", false);
        String error = getSharedPreferences(NavigationService.PREFERENCES, MODE_PRIVATE)
                .getString("last_error", "");
        status.setText("\nControls requested: " + (enabled ? "yes" : "no")
                + "\nAccessibility service connected: " + (NavigationService.isConnected() ? "yes" : "no")
                + (error.length() == 0 ? "" : "\n" + error) + "\n");
    }
}
