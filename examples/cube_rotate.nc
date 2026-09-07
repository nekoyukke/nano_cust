class Vector3 {
    let ox: number;
    let oy: number;
    let oz: number;

    let x: number;
    let y: number;
    let z: number;

    fn init(x_: number, y_: number, z_: number) -> int {
        ox = x_;
        oy = y_;
        oz = z_;

        x = x_;
        y = y_;
        z = z_;

        return 0;
    }

    fn rotate(
        angle_x: number,
        angle_y: number,
        angle_z: number
    ) -> int {

        // X軸回転
        let x1: number = ox;
        let y1: number =
            oy * Cos(angle_x)
            - oz * Sin(angle_x);

        let z1: number =
            oy * Sin(angle_x)
            + oz * Cos(angle_x);


        // Y軸回転
        let x2: number =
            x1 * Cos(angle_y)
            + z1 * Sin(angle_y);

        let y2: number = y1;

        let z2: number =
            -x1 * Sin(angle_y)
            + z1 * Cos(angle_y);


        // Z軸回転
        let x3: number =
            x2 * Cos(angle_z)
            - y2 * Sin(angle_z);

        let y3: number =
            x2 * Sin(angle_z)
            + y2 * Cos(angle_z);

        let z3: number = z2;


        x = x3;
        y = y3;
        z = z3;

        return 0;
    }

    fn camera_x() -> number {
        let depth: number = 7 - z;
        return x * 180 / depth;
    }

    fn camera_y() -> number {
        let depth: number = 7 - z;
        return y * 180 / depth;
    }
}


sprite Main {

    fn draw_line(
        a: Vector3,
        b: Vector3
    ) -> int {

        PenUp();

        Move(
            a.camera_x(),
            a.camera_y()
        );

        PenDown();

        Move(
            b.camera_x(),
            b.camera_y()
        );

        PenUp();

        return 0;
    }


    fn main() -> int {

        let p1: Vector3 = new Vector3;
        let p2: Vector3 = new Vector3;
        let p3: Vector3 = new Vector3;
        let p4: Vector3 = new Vector3;

        let p5: Vector3 = new Vector3;
        let p6: Vector3 = new Vector3;
        let p7: Vector3 = new Vector3;
        let p8: Vector3 = new Vector3;


        // 奥の面
        p1.init(-1.5, -1.5, -1.5);
        p2.init( 1.5, -1.5, -1.5);
        p3.init( 1.5,  1.5, -1.5);
        p4.init(-1.5,  1.5, -1.5);

        // 手前の面
        p5.init(-1.5, -1.5,  1.5);
        p6.init( 1.5, -1.5,  1.5);
        p7.init( 1.5,  1.5,  1.5);
        p8.init(-1.5,  1.5,  1.5);


        let angle_x: number = 0;
        let angle_y: number = 0;
        let angle_z: number = 0;


        PenColor("#00aaff");
        PenSize(2);

        ClearPen();


        while 1 == 1 {

            // 角度だけを増やす
            angle_x = angle_x + 1;
            angle_y = angle_y + 2;
            angle_z = angle_z + 0.5;


            // 全頂点を「元の座標」から回転
            p1.rotate(angle_x, angle_y, angle_z);
            p2.rotate(angle_x, angle_y, angle_z);
            p3.rotate(angle_x, angle_y, angle_z);
            p4.rotate(angle_x, angle_y, angle_z);

            p5.rotate(angle_x, angle_y, angle_z);
            p6.rotate(angle_x, angle_y, angle_z);
            p7.rotate(angle_x, angle_y, angle_z);
            p8.rotate(angle_x, angle_y, angle_z);


            ClearPen();


            // 奥の四角形
            draw_line(p1, p2);
            draw_line(p2, p3);
            draw_line(p3, p4);
            draw_line(p4, p1);


            // 手前の四角形
            draw_line(p5, p6);
            draw_line(p6, p7);
            draw_line(p7, p8);
            draw_line(p8, p5);


            // 奥と手前を接続
            draw_line(p1, p5);
            draw_line(p2, p6);
            draw_line(p3, p7);
            draw_line(p4, p8);
        }

        return 0;
    }
}
