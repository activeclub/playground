import argparse

import genesis as gs
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--vis", action="store_true", default=False)
    args = parser.parse_args()

    ########################## init ##########################
    gs.init(
        backend=gs.gpu,
        precision="32",
        logging_level="info",
        theme="dark",
    )

    ########################## create a scene ##########################

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(),
        viewer_options=gs.options.ViewerOptions(
            camera_pos=(3.5, 1.0, 2.5),
            camera_lookat=(0.0, 1.0, 0.5),
            camera_fov=40,
        ),
        show_viewer=args.vis,
        rigid_options=gs.options.RigidOptions(
            dt=0.01,
        ),
    )

    ########################## entities ##########################
    plane = scene.add_entity(gs.morphs.Plane())
    # scene.add_entity(gs.morphs.Box(pos=(0.0, 0.5, 1.0), size=(0.2, 0.2, 0.2)))
    # scene.add_entity(gs.morphs.Cylinder(pos=(0.0, 1.0, 1.0), height=0.2, radius=0.1))
    # scene.add_entity(gs.morphs.Sphere(pos=(0.0, 1.5, 1.0), radius=0.2))

    franka = scene.add_entity(
        gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml"),
    )

    cam = scene.add_camera(
        res=(1280, 960), pos=(3.5, 0.0, 2.5), lookat=(0, 0, 0.5), fov=40, GUI=False
    )

    ########################## build ##########################
    B = 20
    scene.build(n_envs=B, env_spacing=(1.0, 1.0))

    jnt_names = [
        "joint1",
        "joint2",
        "joint3",
        "joint4",
        "joint5",
        "joint6",
        "joint7",
        "finger_joint1",
        "finger_joint2",
    ]
    dofs_idx = [franka.get_joint(name).dof_idx_local for name in jnt_names]

    ############ Optional: set control gains ############
    # set positional gains
    franka.set_dofs_kp(
        kp=np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]),
        dofs_idx_local=dofs_idx,
    )
    # set velocity gains
    franka.set_dofs_kv(
        kv=np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]),
        dofs_idx_local=dofs_idx,
    )
    # set force range for safety
    franka.set_dofs_force_range(
        lower=np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
        upper=np.array([87, 87, 87, 87, 12, 12, 12, 100, 100]),
        dofs_idx_local=dofs_idx,
    )

    # gs.tools.run_in_another_thread(fn=run_sim, args=(scene, args.vis, franka, dofs_idx))
    gs.tools.run_in_another_thread(fn=record_cam, args=(scene, cam, franka, dofs_idx))

    if args.vis:
        scene.viewer.start()


def control(step, franka, dofs_idx):
    # PD control
    if step == 0:
        franka.control_dofs_position(
            np.array([1, 1, 0, 0, 0, 0, 0, 0.04, 0.04]),
            dofs_idx,
        )
    elif step == 250:
        franka.control_dofs_position(
            np.array([-1, 0.8, 1, -2, 1, 0.5, -0.5, 0.04, 0.04]),
            dofs_idx,
        )
    elif step == 500:
        franka.control_dofs_position(
            np.array([0, 0, 0, 0, 0, 0, 0, 0, 0]),
            dofs_idx,
        )
    elif step == 750:
        # control first dof with velocity, and the rest with position
        franka.control_dofs_position(
            np.array([0, 0, 0, 0, 0, 0, 0, 0, 0])[1:],
            dofs_idx[1:],
        )
        franka.control_dofs_velocity(
            np.array([1.0, 0, 0, 0, 0, 0, 0, 0, 0])[:1],
            dofs_idx[:1],
        )
    elif step == 1000:
        franka.control_dofs_force(
            np.array([0, 0, 0, 0, 0, 0, 0, 0, 0]),
            dofs_idx,
        )
    # This is the control force computed based on the given control command
    # If using force control, it's the same as the given control command
    # print("control force:", franka.get_dofs_control_force(dofs_idx))

    # # This is the actual force experienced by the dof
    # print("internal force:", franka.get_dofs_force(dofs_idx))



def record_cam(scene: gs.Scene, cam, franka, dofs_idx):
    cam.start_recording()
    cam.set_pose(
        pos=(2.0, -2.0, 2.0),
        lookat=(0.5, 0.0, 0.5),
    )

    for i in range(240):
        control(i, franka, dofs_idx)
        scene.step()
        cam.render()
    cam.stop_recording(save_to_filename="video.mp4", fps=60)


def run_sim(scene: gs.Scene, enable_vis, franka, dofs_idx):
    from time import time

    t_prev = time()
    i = 0
    while True:
        i += 1

        scene.step()

        t_now = time()
        print(1 / (t_now - t_prev), "FPS")
        t_prev = t_now
        if i > 1_000_000:
            break

    if enable_vis:
        scene.viewer.stop()


if __name__ == "__main__":
    main()