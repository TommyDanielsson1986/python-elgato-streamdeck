import json
import time
import os
import tkinter as tk
from obsws_python import ReqClient

is_recording = False  # global flagga för inspelningsstatus

def run_actions(client, actions):
    global is_recording
    for action in actions:
        command = action.get("command")
        params = action.get("params", {})
        delay = action.get("delay", 0)

        if command == "set_scene":
            scene_name = params.get("sceneName")
            if scene_name:
                print(f"📺 Byter scen till: {scene_name}")
                client.set_current_program_scene(scene_name)

        elif command in ("hide_source", "show_source"):
            scene_name = params.get("sceneName")
            source_name = params.get("sourceName")
            if not scene_name or not source_name:
                print("⚠️ Saknas sceneName eller sourceName i params")
                continue
            try:
                response = client.get_scene_item_list(scene_name)
                scene_items = response['sceneItems'] if isinstance(response, dict) else response.scene_items
                item = next(i for i in scene_items if i['sourceName'] == source_name)
                item_id = item['sceneItemId']
                visible = (command == "show_source")
                print(f"{'👁️ Visar' if visible else '🙈 Dölj'} '{source_name}' i scen '{scene_name}'")
                client.set_scene_item_enabled(scene_name, item_id, visible)
            except Exception as e:
                print(f"❌ Fel vid toggle_source: {e}")

        elif command == "toggle_record":
            client.toggle_record()
            is_recording = not is_recording
            print("🎬 Filming pågår!" if is_recording else "⏹️ Filming avslutades!")

        elif command == "start_streaming":
            client.start_stream()
            print("🎥 Startar Stream")

        elif command == "stop_stream":
            print("⏳ Väntar 30 sekunder innan stream stoppas...")
            time.sleep(30)
            client.stop_stream()
            print("🛑 Stream Avslutat")

        elif command == "quit":
            print("⚠️ Avslutar programmet")
            root.quit()
            os._exit(0)

        else:
            print(f"⚠️ Okänt kommando: {command}")

        if delay > 0:
            time.sleep(delay / 1000)

def main():
    global root
    with open("obs.conf") as f:
        config = json.load(f)
    with open("profiles.json") as f:
        profiles = json.load(f)

    # välj profil
    print("Profiler:")
    for key, profil in profiles.items():
        print(f"{key}: {profil.get('name')}")
    choice = input("Ange siffra för profil: ").strip()
    profile = profiles[choice]

    client = ReqClient(
        host=config["host"],
        port=config["port"],
        password=config["password"]
    )

    # Byt scensamling om satt
    collection = profile.get("scene_collection")
    if collection:
        try:
            client.send("SetCurrentSceneCollection", {"sceneCollectionName": collection})
            print(f"✅ Scensamling satt till: {collection}")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Kunde inte byta scensamling: {e}")

    scenes = profile.get("scenes", [])
    if not scenes:
        print("Inga scener i vald profil")
        return

    # --- GUI ---
    root = tk.Tk()
    root.title(f"OBS Controller – {profile.get('name')}")
    root.geometry("400x400")

    for scene in scenes:
        name = scene.get("name", "Scene")
        actions = scene.get("actions", [])
        btn = tk.Button(root, text=name, width=20, height=2,
                        command=lambda a=actions: run_actions(client, a))
        btn.pack(pady=5)

    quit_btn = tk.Button(root, text="Avsluta", bg="red", fg="white",
                         command=lambda: run_actions(client, [{"command": "quit"}]))
    quit_btn.pack(side="bottom", pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()