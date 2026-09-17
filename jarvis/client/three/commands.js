export function execute3DCommand(
    scene,
    command
) {

    if (!command) {
        return;
    }

    switch (command.type) {

        case "create_cube": {

            const object =
                scene.createCube(
                    command.id ||
                    "cube"
                );

            if (
                command.position
            ) {

                object.position.set(
                    command.position.x || 0,
                    command.position.y || 0,
                    command.position.z || 0
                );
            }

            if (
                command.scale
            ) {

                object.scale.set(
                    command.scale,
                    command.scale,
                    command.scale
                );
            }

            break;
        }

        case "remove": {

            scene.remove(
                command.id
            );

            break;
        }
    }
}