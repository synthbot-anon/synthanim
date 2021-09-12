import os

PATCH_FOLDER = "C:/Users/synthbot/Desktop/patches"
PATCH = {
    "pre": "Animate - file error - p5v2.exe",
    "post": "Animate - missing font - p6v2.exe",
}

UNDO_TARGETS = [
    {
        "target": "Animate - slow script - p7v2.exe",
        "output": "Animate - slow script - p6v3.exe",
    }
]

if __name__ == "__main__":
    pre_path = os.path.join(PATCH_FOLDER, PATCH["pre"])
    pre_data = open(pre_path, mode="rb").read()
    post_path = os.path.join(PATCH_FOLDER, PATCH["post"])
    post_data = open(post_path, mode="rb").read()

    changes = [
        (index, value)
        for index, value in enumerate(pre_data)
        if post_data[index] != value
    ]

    for target_fn in UNDO_TARGETS:
        target_path = os.path.join(PATCH_FOLDER, target_fn["target"])
        target_data = open(target_path, mode="rb").read()

        output_path = os.path.join(PATCH_FOLDER, target_fn["output"])
        last_index = 0
        with open(output_path, "wb") as output_file:
            for index, value in changes:
                if last_index < index:
                    output_file.write(target_data[last_index:index])
                output_file.write(value.to_bytes(1, "big"))
                last_index = index + 1
            output_file.write(target_data[last_index:])
