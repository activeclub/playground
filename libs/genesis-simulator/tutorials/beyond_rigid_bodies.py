import argparse

import genesis as gs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--vis", action="store_true", default=False)
    args = parser.parse_args()

    ########################## init ##########################
    gs.init(
        backend=gs.cpu,
        precision="32",
        logging_level="info",
        theme="dark",
    )

    ########################## create a scene ##########################


    scene = gs.Scene(
        sim_options=gs.options.SimOptions(
            dt       = 4e-3,
            substeps = 10,
        ),
        mpm_options=gs.options.MPMOptions(
            lower_bound   = (-0.5, -1.0, 0.0),
            upper_bound   = (0.5, 1.0, 1),
        ),
        vis_options=gs.options.VisOptions(
            visualize_mpm_boundary = True,
        ),
        viewer_options=gs.options.ViewerOptions(
            camera_fov=30,
        ),
        show_viewer = True,
    )

    ########################## entities ##########################
    plane = scene.add_entity(gs.morphs.Plane())
    obj_elastic = scene.add_entity(
        material=gs.materials.MPM.Elastic(),
        morph=gs.morphs.Box(
            pos  = (0.0, -0.5, 0.25),
            size = (0.2, 0.2, 0.2),
        ),
        surface=gs.surfaces.Default(
            color    = (1.0, 0.4, 0.4),
            vis_mode = 'visual',
        ),
    )

    obj_sand = scene.add_entity(
        material=gs.materials.MPM.Liquid(),
        morph=gs.morphs.Box(
            pos  = (0.0, 0.0, 0.25),
            size = (0.3, 0.3, 0.3),
        ),
        surface=gs.surfaces.Default(
            color    = (0.3, 0.3, 1.0),
            vis_mode = 'particle',
        ),
    )

    obj_plastic = scene.add_entity(
        material=gs.materials.MPM.ElastoPlastic(),
        morph=gs.morphs.Sphere(
            pos  = (0.0, 0.5, 0.35),
            radius = 0.1,
        ),
        surface=gs.surfaces.Default(
            color    = (0.4, 1.0, 0.4),
            vis_mode = 'particle',
        ),
    )


    cam = scene.add_camera(
        res=(1280, 960), pos=(3.5, 0.0, 2.5), lookat=(0, 0, 0.5), fov=40, GUI=False
    )

    ########################## build ##########################
    scene.build()

    gs.tools.run_in_another_thread(
        fn=run_sim, args=(scene, args.vis, cam)
    )

    if args.vis:
        scene.viewer.start()


def run_sim(scene: gs.Scene, enable_vis, cam):
    if cam:
        cam.start_recording()
        cam.set_pose(
            pos=(6.0, -2.0, 3.0),
            lookat=(1.0, 0.0, 0.5),
        )

    for i in range(1000):
        scene.step()
        if cam:
            cam.render()

    if cam:
        cam.stop_recording(save_to_filename="video.mp4", fps=60)

    if enable_vis:
        scene.viewer.stop()


if __name__ == "__main__":
    main()
