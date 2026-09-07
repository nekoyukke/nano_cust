class Vector3 {
    let x:int;
    let y:int;
    let z:int;

    fn init(x_:int,y_:int,z_:int) -> int {
        x = x_; y = y_; z = z_;
        return 0;
    }
    fn camera_x() -> int {
        return 480*x/z;
    }
    fn camera_y() -> int {
        return 360*y/z;
    }
}

sprite Main {
    fn main() -> int {
        let p1: Vector3 = new Vector3;
        let p2: Vector3 = new Vector3;
        let p3: Vector3 = new Vector3;
        let p4: Vector3 = new Vector3;
        let p5: Vector3 = new Vector3;
        let p6: Vector3 = new Vector3;
        let p7: Vector3 = new Vector3;
        let p8: Vector3 = new Vector3;
        p1.init(3,3,9);
        p2.init(-3,3,9);
        p3.init(3,-3,9);
        p4.init(-3,-3,9);
        p5.init(3,3,6);
        p6.init(-3,3,6);
        p7.init(3,-3,6);
        p8.init(-3,-3,6);
        draw_rect(p1,p2,p3,p4);
        draw_rect(p5,p6,p7,p8);
        draw(p1,p5);
        draw(p2,p6);
        draw(p3,p7);
        draw(p4,p8);
        return 0;
    }

    fn draw(p1:Vector3, p2:Vector3) -> int {
        Move(p1.camera_x(), p1.camera_y());
        PenDown();
        Move(p2.camera_x(), p2.camera_y());
        PenUp();
        return 0;
    }

    fn draw_rect(p1:Vector3, p2:Vector3, p3:Vector3, p4:Vector3) -> int {
        Move(p1.camera_x(), p1.camera_y());
        PenDown();
        Move(p2.camera_x(), p2.camera_y());
        Move(p3.camera_x(), p3.camera_y());
        Move(p4.camera_x(), p4.camera_y());
        Move(p1.camera_x(), p1.camera_y());
        PenUp();
        return 0;
    }
}