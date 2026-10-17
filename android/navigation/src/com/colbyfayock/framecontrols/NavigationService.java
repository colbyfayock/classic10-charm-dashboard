package com.colbyfayock.framecontrols;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Point;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.Toast;

public final class NavigationService extends AccessibilityService {
    static final String PREFERENCES = "frame_controls";
    private static NavigationService connected;
    private WindowManager windows;
    private WindowManager.LayoutParams position;
    private View panel;

    static boolean isConnected() {
        return connected != null;
    }

    static void refreshConnected() {
        if (connected != null) {
            connected.refresh();
        }
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        AccessibilityServiceInfo info = getServiceInfo();
        info.eventTypes = 0;
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
        info.flags = 0;
        info.notificationTimeout = 0;
        setServiceInfo(info);
        connected = this;
        windows = (WindowManager) getSystemService(WINDOW_SERVICE);
        refresh();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // No event subscriptions, event inspection, or screen-content retrieval.
    }

    @Override
    public void onInterrupt() {
        hide();
    }

    private SharedPreferences preferences() {
        return getSharedPreferences(PREFERENCES, MODE_PRIVATE);
    }

    private void refresh() {
        if (!ControlPolicy.shouldShow(preferences().getBoolean("enabled", false), connected == this)) {
            hide();
            return;
        }
        if (panel != null) {
            return;
        }
        final LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.setBackgroundColor(Color.rgb(235, 235, 235));
        Button move = button(controls, "Move", "Drag to move controls", null);
        button(controls, "Back", "Android Back", new View.OnClickListener() {
            @Override public void onClick(View view) {
                global(GLOBAL_ACTION_BACK);
            }
        });
        button(controls, "Home", "Android Home", new View.OnClickListener() {
            @Override public void onClick(View view) {
                global(GLOBAL_ACTION_HOME);
            }
        });
        button(controls, "Hide", "Stop these controls", new View.OnClickListener() {
            @Override public void onClick(View view) {
                preferences().edit().putBoolean("enabled", false).apply();
                hide();
            }
        });
        position = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_PHONE,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT);
        position.gravity = Gravity.TOP | Gravity.LEFT;
        position.x = preferences().getInt("x", dp(12));
        position.y = preferences().getInt("y", dp(24));
        panel = controls;
        clamp();
        move.setOnTouchListener(new View.OnTouchListener() {
            private float downX;
            private float downY;
            private int startX;
            private int startY;
            private boolean dragging;

            @Override public boolean onTouch(View view, MotionEvent event) {
                switch (event.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        downX = event.getRawX();
                        downY = event.getRawY();
                        startX = position.x;
                        startY = position.y;
                        dragging = false;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        float dx = event.getRawX() - downX;
                        float dy = event.getRawY() - downY;
                        dragging |= ControlPolicy.isDrag(dx, dy, getResources().getDisplayMetrics().density);
                        if (dragging) {
                            position.x = startX + Math.round(dx);
                            position.y = startY + Math.round(dy);
                            clamp();
                            windows.updateViewLayout(panel, position);
                        }
                        return true;
                    case MotionEvent.ACTION_UP:
                    case MotionEvent.ACTION_CANCEL:
                        if (dragging) {
                            preferences().edit().putInt("x", position.x).putInt("y", position.y).apply();
                        } else if (event.getActionMasked() == MotionEvent.ACTION_UP) {
                            view.performClick();
                        }
                        return true;
                    default:
                        return true;
                }
            }
        });
        try {
            windows.addView(panel, position);
        } catch (SecurityException error) {
            overlayFailed();
        } catch (WindowManager.BadTokenException error) {
            overlayFailed();
        }
    }

    private Button button(LinearLayout parent, String label, String description, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(14);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setContentDescription(description);
        button.setOnClickListener(listener);
        parent.addView(button, new LinearLayout.LayoutParams(dp(68), dp(52)));
        return button;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void clamp() {
        Point screen = new Point();
        windows.getDefaultDisplay().getRealSize(screen);
        panel.measure(View.MeasureSpec.makeMeasureSpec(screen.x, View.MeasureSpec.AT_MOST),
                View.MeasureSpec.makeMeasureSpec(screen.y, View.MeasureSpec.AT_MOST));
        position.x = ControlPolicy.clamp(position.x, screen.x, panel.getMeasuredWidth());
        position.y = ControlPolicy.clamp(position.y, screen.y, panel.getMeasuredHeight());
    }

    private void global(int action) {
        if (!performGlobalAction(action)) {
            Toast.makeText(this, "Android did not accept that navigation action.", Toast.LENGTH_SHORT).show();
        }
    }

    private void overlayFailed() {
        panel = null;
        preferences().edit().putBoolean("enabled", false)
                .putString("last_error", "Android rejected the overlay. Keep ADB available; no system setting was changed.")
                .apply();
        Toast.makeText(this, "Overlay unavailable. Open Frame Controls for status.", Toast.LENGTH_LONG).show();
    }

    private void hide() {
        if (panel != null) {
            windows.removeView(panel);
            panel = null;
        }
    }

    @Override
    public void onConfigurationChanged(Configuration configuration) {
        super.onConfigurationChanged(configuration);
        if (panel != null) {
            clamp();
            windows.updateViewLayout(panel, position);
        }
    }

    @Override
    public boolean onUnbind(Intent intent) {
        hide();
        if (connected == this) {
            connected = null;
        }
        return super.onUnbind(intent);
    }

    @Override
    public void onDestroy() {
        hide();
        if (connected == this) {
            connected = null;
        }
        super.onDestroy();
    }
}
