import json
import time
import io
import os
from obsws_python import ReqClient
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager

is_recording = False  # Definiera global flagga för inspelningsstatus här

def pil_image_to_streamdeck_format(pil_image, size):
    image = pil_image.resize(size)
    rotated = image.rotate(90, expand=True)
    flipped = rotated.transpose(Image.FLIP_TOP_BOTTOM)
    with io.BytesIO() as output:
        flipped.save(output, format='BMP')
        return output.getvalue()

def load_font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except IOError:
        return ImageFont.load_default()

def create_button_image(size, color, text, text_color=(255, 255, 255)):
    width, height = size
    image = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(image)
    font_size = max(12, height // 4)
    font = load_font(font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2

    draw.text((text_x, text_y), text, font=font, fill=text_color)
    return image

def run_actions(client, actions, deck):
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

        elif command == "hide_source" or command == "show_source":
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

            except StopIteration:
                print(f"⚠️ Kunde inte hitta källa '{source_name}' i scen '{scene_name}'")
            except Exception as e:
                print(f"❌ Fel vid toggle_source: {e}")

        elif command == "toggle_record":
            client.toggle_record()
            is_recording = not is_recording
            if is_recording:
                print("🎬 Filming pågår!")
            else:
                print("⏹️ Filming avslutades!")

        elif command == "start_streaming":
            client.start_stream()
            print("🎥 Startar Stream")

        elif command == "stop_stream":
            print("⏳ Väntar 30 sekunder innan stream stoppas och program avslutas...")
            time.sleep(30)
            client.stop_stream()
            print("🛑 Stream Avslutat")

        elif command == "quit":
            print("⚠️ Stream Deck stängt av")
            deck.reset()
            deck.close()
            os._exit(0)
            
        else:
            print(f"⚠️ Okänd command: {command}")

        if delay > 0:
            time.sleep(delay / 1000)

def choose_profile(profiles):
    print("Välj profil/scensamling:")
    for key, profil in profiles.items():
        print(f"{key}: {profil.get('name')} (scene_collection: {profil.get('scene_collection')})")

    while True:
        choice = input("Ange siffra för profil: ").strip()
        if choice in profiles:
            return profiles[choice]
        else:
            print("Ogiltigt val, försök igen.")

def setup_button_images(profile, size):
    images = []
    scenes = profile.get("scenes", [])
    for scene in scenes:
        color = tuple(scene.get("color", (50, 50, 50)))
        text_color = tuple(scene.get("text_color", (255, 255, 255)))
        name = scene.get("name", "Scene")
        print(f"🖼️ Skapar bild för scen '{name}' med färg {color} och textfärg {text_color}")
        img = create_button_image(size, color, name, text_color=text_color)
        images.append(img)
    return images

def main():
    with open("obs.conf") as f:
        config = json.load(f)

    with open("profiles.json") as f:
        profiles = json.load(f)

    profile = choose_profile(profiles)
    print(f"Vald profil: {profile.get('name')}")

    client = ReqClient(
        host=config["host"],
        port=config["port"],
        password=config["password"]
    )

    # Försök byta scensamling
    collection = profile.get("scene_collection")
    if collection:
        try:
            client.send("SetCurrentSceneCollection", {"sceneCollectionName": collection})
            print(f"✅ Scensamling satt till: {collection}")
            time.sleep(2)  # ge OBS lite tid att byta
        except Exception as e:
            print(f"❌ Kunde inte byta scensamling: {e}")

    scenes = profile.get("scenes", [])
    if not scenes:
        print("Inga scener i vald profil")
        return

    streamdecks = DeviceManager().enumerate()
    if not streamdecks:
        print("Ingen Stream Deck hittad!")
        return

    deck = streamdecks[0]
    deck.open()
    deck.reset()

    size = deck.key_image_format()['size']
    print(f"Knappstorlek: {size}")

    button_images = setup_button_images(profile, size)

    for i, img in enumerate(button_images):
        img_bytes = pil_image_to_streamdeck_format(img, size)
        deck.set_key_image(i, img_bytes)

    print("Knappar satta! Tryck på knapparna på Stream Deck... (Ctrl+C för att avsluta)")

    def key_change_callback(deck, key, state):
        if state:
            if key < len(scenes):
                scene = scenes[key]
                print(f"Knapp {key+1} → Kör actions för scen: {scene.get('name')}")
                actions = scene.get("actions", [])
                run_actions(client, actions, deck)

    deck.set_key_callback(key_change_callback)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Avslutar...")
        deck.reset()
        deck.close()

if __name__ == "__main__":
    main()
