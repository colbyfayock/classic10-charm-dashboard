package com.colbyfayock.framecontrols;

/** Platform-independent safety and positioning rules shared with host tests. */
public final class ControlPolicy {
    private ControlPolicy() {}

    public static boolean shouldShow(boolean enabled, boolean connected) {
        return enabled && connected;
    }

    public static int clamp(int position, int screenSize, int panelSize) {
        int maximum = Math.max(0, screenSize - Math.max(0, panelSize));
        return Math.max(0, Math.min(position, maximum));
    }

    public static boolean isDrag(float dx, float dy, float density) {
        if (density <= 0 || Float.isNaN(density) || Float.isInfinite(density)
                || Float.isNaN(dx) || Float.isNaN(dy)
                || Float.isInfinite(dx) || Float.isInfinite(dy)) {
            return false;
        }
        double threshold = 8.0 * density;
        return (double) dx * dx + (double) dy * dy > threshold * threshold;
    }
}
