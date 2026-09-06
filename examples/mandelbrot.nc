// Mandelbrot set renderer for nano_cust / Scratch.
//
// The 120 x 90 sampling grid is enlarged with a pen size of 4, so it fills
// the 480 x 360 Scratch stage while remaining practical to run.
sprite Main {
    fn main() -> int {
        let x: int = 0;
        let y: int = 0;
        let cx: number = 0;
        let cy: number = 0;
        let zx: number = 0;
        let zy: number = 0;
        let next_zx: number = 0;
        let iteration: int = 0;

        ClearPen();
        PenColor("#000000");
        PenSize(4);

        while y < 90 {
            x = 0;
            while x < 120 {
                // Map the grid onto the conventional complex-plane region:
                // -2.0 <= Re(c) < 1.0 and -1.5 <= Im(c) < 1.5.
                cx = x / 40 - 2;
                cy = y / 30 - 1.5;
                zx = 0;
                zy = 0;
                iteration = 0;

                // z(n + 1) = z(n)^2 + c.  Escape is certain once |z|^2 > 4.
                while iteration < 50 && zx * zx + zy * zy <= 4 {
                    next_zx = zx * zx - zy * zy + cx;
                    zy = 2 * zx * zy + cy;
                    zx = next_zx;
                    iteration = iteration + 1;
                }

                // Points which did not escape are considered part of the set.
                if iteration == 50 {
                    PenUp();
                    Move(x * 4 - 240, y * 4 - 180);
                    PenDown();
                    Move(x * 4 - 236, y * 4 - 180);
                }
                x = x + 1;
            }
            y = y + 1;
        }
        PenUp();
        return 0;
    }
}
