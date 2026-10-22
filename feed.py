import argparse
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import yaml


ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"
ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("atom", ATOM_NS)


def add_text(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = str(text)
    return element


def required_text(data, key, context):
    value = data.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"Missing required {context} field: {key}")
    return str(value).strip()


def asset_url(base_url, path):
    return urljoin(base_url.rstrip("/") + "/", str(path).lstrip("/"))


def build_feed(data, base_url):
    channel_link = base_url.rstrip("/")
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")

    title = required_text(data, "title", "feed")
    description = required_text(data, "description", "feed")
    author = required_text(data, "author", "feed")
    image_url = asset_url(base_url, required_text(data, "image", "feed"))

    add_text(channel, "title", title)
    add_text(channel, "link", channel_link)
    add_text(channel, "description", description)
    add_text(channel, "language", required_text(data, "language", "feed"))
    ET.SubElement(channel, f"{{{ATOM_NS}}}link", {
        "href": asset_url(base_url, "podcast.xml"),
        "rel": "self",
        "type": "application/rss+xml",
    })

    image = ET.SubElement(channel, "image")
    add_text(image, "url", image_url)
    add_text(image, "title", title)
    add_text(image, "link", channel_link)

    add_text(channel, f"{{{ITUNES_NS}}}author", author)
    add_text(channel, f"{{{ITUNES_NS}}}subtitle", data.get("subtitle", ""))
    add_text(channel, f"{{{ITUNES_NS}}}summary", description)
    ET.SubElement(channel, f"{{{ITUNES_NS}}}image", {"href": image_url})
    category = data.get("category")
    if category:
        ET.SubElement(channel, f"{{{ITUNES_NS}}}category", {"text": str(category)})

    episodes = data.get("item")
    if not isinstance(episodes, list):
        raise ValueError("Feed field 'item' must be a list of episodes")

    audio_type = data.get("format", "audio/mpeg")
    for index, episode in enumerate(episodes, start=1):
        if not isinstance(episode, dict):
            raise ValueError(f"Episode {index} must be a mapping")

        item = ET.SubElement(channel, "item")
        episode_title = required_text(episode, "title", f"episode {index}")
        audio_url = asset_url(base_url, required_text(episode, "file", f"episode {index}"))
        add_text(item, "title", episode_title)
        add_text(item, "description", episode.get("description", ""))
        add_text(item, "pubDate", required_text(episode, "published", f"episode {index}"))
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = audio_url

        raw_length = str(episode.get("length", "")).replace(",", "").strip()
        if not raw_length.isdigit():
            raise ValueError(f"Episode {index} has an invalid or missing audio length")
        ET.SubElement(item, "enclosure", {
            "url": audio_url,
            "length": raw_length,
            "type": str(audio_type),
        })

        if episode.get("duration"):
            add_text(item, f"{{{ITUNES_NS}}}duration", episode["duration"])

    ET.indent(rss, space="  ")
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description="Convert feed.yaml into a podcast RSS feed.")
    parser.add_argument("source", nargs="?", type=Path, default=Path("feed.yaml"))
    parser.add_argument("output", nargs="?", type=Path, default=Path("podcast.xml"))
    parser.add_argument("--base-url", default="https://lyudmilkovachev.github.io/actions-test/")
    args = parser.parse_args()

    with args.source.open(encoding="utf-8") as source_file:
        data = yaml.safe_load(source_file)
    if not isinstance(data, dict):
        parser.error("The YAML document must contain a mapping at its root")

    try:
        xml = build_feed(data, args.base_url)
    except ValueError as error:
        parser.error(str(error))

    args.output.write_bytes(xml)


if __name__ == "__main__":
    main()