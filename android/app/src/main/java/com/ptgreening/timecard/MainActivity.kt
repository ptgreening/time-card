package com.ptgreening.timecard

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat

/**
 * Hosts a single full-screen [CanvasView]. There is no XML layout on purpose: the
 * canvas is the whole window, so the view is set directly as the content view.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var canvasView: CanvasView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        canvasView = CanvasView(this)
        setContentView(canvasView)

        goFullScreen()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        // The system bars come back after a swipe or when focus is regained; re-hide them.
        if (hasFocus) goFullScreen()
    }

    private fun goFullScreen() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, canvasView).apply {
            hide(WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior =
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
    }
}
