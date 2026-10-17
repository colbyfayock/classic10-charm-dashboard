package com.colbyfayock.framecontrols;

public final class ControlPolicyTest {
    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    public static void main(String[] args) {
        check(!ControlPolicy.shouldShow(false, false), "disabled/unbound must hide");
        check(!ControlPolicy.shouldShow(true, false), "unbound must hide");
        check(!ControlPolicy.shouldShow(false, true), "disabled must hide");
        check(ControlPolicy.shouldShow(true, true), "explicit enable and binding required");
        check(ControlPolicy.clamp(-20, 800, 100) == 0, "negative position");
        check(ControlPolicy.clamp(900, 800, 100) == 700, "right boundary");
        check(ControlPolicy.clamp(80, 50, 100) == 0, "panel larger than screen");
        check(ControlPolicy.clamp(200, 1280, 200) == 200, "valid position");
        check(ControlPolicy.clamp(700, 600, 200) == 400, "rotation resize");
        check(!ControlPolicy.isDrag(3, 4, 1), "small move is not a drag");
        check(!ControlPolicy.isDrag(8, 0, 1), "threshold is not a drag");
        check(ControlPolicy.isDrag(9, 0, 1), "movement beyond threshold");
        check(!ControlPolicy.isDrag(9, 0, 2), "density-aware threshold");
        check(!ControlPolicy.isDrag(20, 20, 0), "invalid density must not drag");
        check(!ControlPolicy.isDrag(Float.NaN, 20, 1), "non-finite input");
        check(!ControlPolicy.isDrag(Float.POSITIVE_INFINITY, 0, 1), "non-finite movement");
        System.out.println("Navigation policy assertions passed.");
    }
}
