"""
Pre-written Panchatantra story templates for video generation.

Each story is keyed by a URL-friendly slug and contains:
  - title:          Human-readable story name
  - narrator_intro: Opening narration text
  - scenes:         List of scene dicts with video_prompt for MetaAI
"""

STORIES: dict[str, dict] = {
    # ------------------------------------------------------------------ #
    #  1. The Monkey and the Crocodile
    # ------------------------------------------------------------------ #
    "monkey-and-crocodile": {
        "title": "The Monkey and the Crocodile",
        "characters": {
            "monkey": (
                "A golden-brown rhesus monkey with a cream-colored belly, "
                "bright amber eyes, small rounded ears, and a long curling "
                "tail. Lean and agile build, expressive face with pale skin "
                "around the eyes and muzzle."
            ),
            "crocodile": (
                "A large dark-green mugger crocodile with a broad flat snout, "
                "a yellow underbelly, ridged scaly back, powerful thick tail, "
                "and small beady yellow eyes. Approximately twelve feet long."
            ),
            "crocodile_wife": (
                "A smaller olive-green female mugger crocodile with a narrower "
                "snout than her mate, lighter yellow-green underbelly, and "
                "slightly smoother scales. About nine feet long."
            ),
        },
        "character_prompt": (
            "A golden-brown rhesus monkey with a cream belly sitting on the "
            "back of a large dark-green mugger crocodile with a yellow "
            "underbelly, beside a smaller olive-green female crocodile, all "
            "together on a sunny tropical riverbank. Full body view of all "
            "three characters, bright daylight, photorealistic style."
        ),
        "narrator_intro": (
            "Long ago, on the banks of a great river, a clever monkey and "
            "a hungry crocodile formed an unlikely friendship — until greed "
            "threatened to destroy it."
        ),
        "narrator_outro": (
            "Safe among the branches, the monkey declared their friendship "
            "over, for trust once broken can never be mended. And so the "
            "clever monkey lived on, wiser for the betrayal he had survived."
        ),
        "scenes": [
            {
                "scene_number": 1,
                "description": "The monkey's home by the river",
                "narration": (
                    "Once upon a time, a clever monkey lived in a tall jamun "
                    "tree on the banks of a mighty river. He spent his days "
                    "swinging through the branches and feasting on sweet purple "
                    "fruit. Life was peaceful, and the monkey wanted for nothing."
                ),
                "video_prompt": (
                    "A golden-brown rhesus monkey with a cream belly sits on a "
                    "high branch of a tall jamun tree heavy with dark purple "
                    "fruit, eating and gazing at the shimmering river below. "
                    "Lush tropical riverbank at golden hour. Cinematic wide "
                    "shot, warm sunlight filtering through dense green canopy, "
                    "gentle river current, butterflies drifting in the air. "
                    "Photorealistic style."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 2,
                "description": "The crocodile appears",
                "narration": (
                    "One day, a hungry crocodile swam up to the riverbank and "
                    "gazed longingly at the fruit tree. He had traveled far and "
                    "was terribly tired and famished. The monkey noticed the "
                    "weary stranger below and felt a surge of compassion."
                ),
                "video_prompt": (
                    "A large dark-green mugger crocodile with a yellow underbelly "
                    "slowly surfaces from a calm tropical river, eyes just above "
                    "the waterline, looking up at a fruit tree on the bank. "
                    "Ripples spread across the golden-lit water. Low-angle "
                    "cinematic shot from water level, lush vegetation reflected "
                    "in the river, late afternoon light. Dramatic and peaceful."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 3,
                "description": "Monkey shares fruit with the crocodile",
                "narration": (
                    "The kind-hearted monkey plucked ripe jamun fruits and "
                    "tossed them down to the crocodile. The crocodile devoured "
                    "them gratefully, having never tasted anything so sweet. "
                    "From that day on, the two met every afternoon, and a warm "
                    "friendship blossomed between them."
                ),
                "video_prompt": (
                    "A golden-brown rhesus monkey with a cream belly on a low "
                    "branch drops ripe purple jamun fruits into the open jaws "
                    "of a large dark-green mugger crocodile with a yellow "
                    "underbelly floating below. Close-up shot, fruit falling in "
                    "slow motion, splashing near the crocodile's snout. Warm "
                    "tropical lighting, vibrant greens and purples."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 4,
                "description": "Crocodile brings fruit home to his wife",
                "narration": (
                    "The crocodile began carrying fruits home to his wife on "
                    "their island in the river. She savored the delicious jamun "
                    "and grew curious about where they came from. When the "
                    "crocodile spoke of his dear friend the monkey, a wicked "
                    "idea took root in her mind."
                ),
                "video_prompt": (
                    "A large dark-green mugger crocodile with a yellow "
                    "underbelly swimming through a wide river carrying purple "
                    "fruits in its mouth, approaching a sandy riverbank island "
                    "where a smaller olive-green female crocodile waits. Aerial "
                    "tracking shot through crystal-clear blue-green water. "
                    "Sunset colors reflecting off the river surface."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 5,
                "description": "The wife demands the monkey's heart",
                "narration": (
                    "The crocodile's wife declared that if the fruit was so "
                    "sweet, the monkey's heart must be even sweeter. She "
                    "demanded her husband bring her the monkey's heart, or she "
                    "would never speak to him again. The crocodile was "
                    "horrified, but his wife would not relent."
                ),
                "video_prompt": (
                    "A smaller olive-green female crocodile snapping her jaws "
                    "aggressively at a large dark-green mugger crocodile with "
                    "a yellow underbelly on a moonlit sandy riverbank. The male "
                    "appears troubled and conflicted. Dramatic low-key lighting "
                    "with silver moonlight, dark river in background, tense "
                    "atmosphere. Close-up on expressive reptilian eyes."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 6,
                "description": "Crocodile invites monkey for a ride",
                "narration": (
                    "Torn between loyalty to his friend and his wife's cruel "
                    "demand, the crocodile hatched a terrible plan. He invited "
                    "the monkey to ride on his back across the river to attend "
                    "a grand feast. The trusting monkey eagerly climbed aboard, "
                    "delighted at the unexpected adventure."
                ),
                "video_prompt": (
                    "A golden-brown rhesus monkey with a cream belly cheerfully "
                    "climbing onto the broad back of a large dark-green mugger "
                    "crocodile with a yellow underbelly at the river's edge. "
                    "Morning sunlight sparkles on the water. Medium shot, lush "
                    "tropical backdrop with palm trees and flowering plants. "
                    "Bright, deceptively cheerful color palette."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 7,
                "description": "The crocodile reveals his plan mid-river",
                "narration": (
                    "When they reached the deepest part of the river, the "
                    "crocodile began to sink beneath the water. He confessed "
                    "the terrible truth — his wife wanted the monkey's heart. "
                    "The monkey's blood ran cold, but he kept his wits about him."
                ),
                "video_prompt": (
                    "A golden-brown rhesus monkey with a cream belly riding on "
                    "the back of a large dark-green mugger crocodile with a "
                    "yellow underbelly in the middle of a vast deep river. The "
                    "crocodile begins to submerge slowly. The monkey grips "
                    "tightly, alarmed. Dramatic wide shot, stormy clouds "
                    "overhead. Desaturated blues and greens, tension building."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 8,
                "description": "Monkey's clever trick — heart left in the tree",
                "narration": (
                    "Thinking quickly, the monkey laughed and said he had left "
                    "his heart safely hanging in the jamun tree. He urged the "
                    "crocodile to turn back so he could fetch it. The foolish "
                    "crocodile believed every word and swam back toward the shore."
                ),
                "video_prompt": (
                    "Close-up of a golden-brown rhesus monkey with a cream "
                    "belly on the back of a large dark-green mugger crocodile "
                    "in deep river water, gesturing animatedly toward the "
                    "distant riverbank where a tall fruit tree is visible. "
                    "Cunning expression on the monkey's face. Camera slowly "
                    "zooms toward the tree. Rays of sunlight breaking through "
                    "clouds."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 9,
                "description": "Monkey escapes up the tree",
                "narration": (
                    "The moment they reached the riverbank, the monkey leaped "
                    "off the crocodile's back and scrambled up the tree in a "
                    "flash. He perched on the highest branch, his heart pounding "
                    "with relief. The crocodile realized too late that he had "
                    "been outwitted."
                ),
                "video_prompt": (
                    "A golden-brown rhesus monkey with a cream belly leaping "
                    "off the back of a large dark-green mugger crocodile with "
                    "a yellow underbelly at the river's edge and scrambling "
                    "rapidly up a tall jamun tree trunk. Dynamic action shot "
                    "with motion blur, the crocodile lunging but missing. "
                    "Bright triumphant lighting, slow-motion decisive leap."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 10,
                "description": "Moral — the monkey safe in the tree",
                "narration": (
                    "Safe among the branches, the monkey looked down at his "
                    "former friend with sadness. He declared their friendship "
                    "over, for trust once broken can never be mended. And so "
                    "the clever monkey lived on, wiser for the betrayal he "
                    "had survived."
                ),
                "video_prompt": (
                    "A golden-brown rhesus monkey with a cream belly sitting "
                    "safely on the highest branch of a tall fruit tree, looking "
                    "down at a large dark-green mugger crocodile with a yellow "
                    "underbelly sinking back into the river far below. Golden "
                    "sunset backlighting, monkey silhouetted against an orange "
                    "sky. Majestic wide shot, warm cinematic palette."
                ),
                "duration_hint": 20,
            },
        ],
    },
    # ------------------------------------------------------------------ #
    #  2. The Tortoise and the Geese
    # ------------------------------------------------------------------ #
    "tortoise-and-geese": {
        "title": "The Tortoise and the Geese",
        "characters": {
            "tortoise": (
                "An olive-green tortoise with a high domed shell patterned "
                "with orange spots, wrinkled leathery skin on the neck and "
                "legs, small dark eyes, and a blunt rounded beak. About two "
                "feet long from head to tail."
            ),
            "goose_1": (
                "An elegant white goose with bright orange beak, orange "
                "webbed feet, long graceful neck, black-tipped wing feathers, "
                "and small dark eyes. Sleek plumage with a slight pearly sheen."
            ),
            "goose_2": (
                "An elegant white goose identical to the first — bright orange "
                "beak, orange webbed feet, long graceful neck, black-tipped "
                "wing feathers, and small dark eyes. Sleek pearly-white plumage."
            ),
        },
        "character_prompt": (
            "An olive-green tortoise with a domed shell and orange spots "
            "standing between two elegant white geese with orange beaks and "
            "orange feet, all on the shore of a small lake. Full body view "
            "of all three characters, bright daylight, photorealistic style."
        ),
        "narrator_intro": (
            "A talkative tortoise and two loyal geese friends devised a plan "
            "to fly to a new lake — but the tortoise's inability to stay "
            "silent would prove fatal."
        ),
        "narrator_outro": (
            "The two geese flew on to the new lake, their hearts heavy with "
            "grief for their lost friend. The tale reminds us that silence, "
            "at the right moment, can save our very lives."
        ),
        "scenes": [
            {
                "scene_number": 1,
                "description": "A drying lake in the heat",
                "narration": (
                    "In a distant corner of the land, a small lake was slowly "
                    "drying up under the relentless summer sun. A tortoise who "
                    "had lived there all his life watched the water shrink day "
                    "by day. With each passing morning, his worry grew deeper."
                ),
                "video_prompt": (
                    "An olive-green tortoise with a domed shell and orange "
                    "spots sits at the edge of a small lake drying up in an "
                    "arid Indian landscape under a scorching sun. Cracked mud "
                    "at the shrinking edges, sparse dry grass. Wide "
                    "establishing shot, parched earth tones, heat haze "
                    "shimmering above the ground, dramatic harsh white sunlight."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 2,
                "description": "Two geese visit the tortoise",
                "narration": (
                    "Two geese, old friends of the tortoise, flew down from "
                    "the sky one afternoon. They brought news of a beautiful "
                    "lake far to the north, brimming with clear water. They "
                    "urged the tortoise to come with them before it was too late."
                ),
                "video_prompt": (
                    "Two elegant white geese with orange beaks and orange feet "
                    "glide down from the sky and land gracefully on the muddy "
                    "shore of a shrinking lake, where an olive-green tortoise "
                    "with a domed shell and orange spots greets them. "
                    "Slow-motion landing, wings spread wide. Warm "
                    "late-afternoon light, dust particles in the air."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 3,
                "description": "The plan — flying with a stick",
                "narration": (
                    "But how could a tortoise fly? The geese devised a clever "
                    "plan — they would carry a stick between their beaks, and "
                    "the tortoise would grip the middle with his mouth. There "
                    "was only one rule: he must not open his mouth, no matter "
                    "what happened."
                ),
                "video_prompt": (
                    "Two elegant white geese with orange beaks and orange feet "
                    "standing on either side of an olive-green tortoise with a "
                    "domed shell and orange spots on dry ground, a long wooden "
                    "stick lying between them. One goose picks up an end of "
                    "the stick in its beak. Medium shot, warm golden light, "
                    "dry savanna background. Photorealistic rendering."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 4,
                "description": "Taking flight together",
                "narration": (
                    "The tortoise bit down firmly on the stick, and the two "
                    "geese took flight. Up and up they soared above the parched "
                    "land, the wind rushing past the tortoise's shell. It was "
                    "the most thrilling moment of his long, slow life."
                ),
                "video_prompt": (
                    "Two elegant white geese with orange beaks and orange feet "
                    "flying upward carrying a long stick between their beaks, "
                    "with an olive-green tortoise with a domed shell and orange "
                    "spots hanging from the middle of the stick by its mouth. "
                    "Dramatic upward tracking shot rising above a dry landscape, "
                    "blue sky with scattered clouds. Exhilarating flight."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 5,
                "description": "Villagers spot the flying tortoise",
                "narration": (
                    "As they flew over a bustling village, the people below "
                    "looked up in astonishment. They had never seen such an "
                    "impossible sight — a tortoise sailing through the sky "
                    "between two geese! They pointed, laughed, and shouted "
                    "mockingly, their voices carrying upward on the wind."
                ),
                "video_prompt": (
                    "A group of people in a rural Indian village looking up at "
                    "the sky in amazement, pointing upward. From their "
                    "perspective, two white geese carrying an olive-green "
                    "tortoise on a stick are visible high above against the "
                    "bright sky. Low-angle shot looking upward, sun flare, "
                    "expressions of wonder and laughter. Vibrant village."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 6,
                "description": "The tortoise opens its mouth",
                "narration": (
                    "The tortoise, proud and talkative by nature, burned with "
                    "the urge to shout back at the mocking crowd. Unable to "
                    "contain himself a moment longer, he opened his mouth to "
                    "speak. In that fatal instant, the stick slipped from his "
                    "jaws."
                ),
                "video_prompt": (
                    "Extreme close-up of an olive-green tortoise with a domed "
                    "shell and orange spots hanging from a wooden stick high "
                    "in the sky, mouth clenched tightly, then slowly opening. "
                    "The stick begins to slip. Wind rushes past, clouds in the "
                    "background. Tense dramatic moment, shallow depth of field, "
                    "slow-motion detail of the grip loosening."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 7,
                "description": "The tortoise falls",
                "narration": (
                    "The tortoise plummeted from the sky, tumbling helplessly "
                    "through the air. The geese cried out in horror but could "
                    "do nothing to save their friend. He crashed to the earth "
                    "below, paying the ultimate price for his inability to "
                    "stay silent."
                ),
                "video_prompt": (
                    "An olive-green tortoise with a domed shell and orange "
                    "spots falling through the sky in slow motion, tumbling "
                    "end over end, the stick and two white geese visible far "
                    "above growing smaller. The ground — a patchwork of fields "
                    "and villages — rushes closer. Vertigo-inducing camera "
                    "angle, tragic cinematography, fading golden light."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 8,
                "description": "Moral — silence is golden",
                "narration": (
                    "The two geese flew on to the new lake, their hearts heavy "
                    "with grief for their lost friend. They had warned him, but "
                    "he would not listen. The tale reminds us that silence, at "
                    "the right moment, can save our very lives."
                ),
                "video_prompt": (
                    "Two elegant white geese with orange beaks and orange feet "
                    "perched on the edge of a beautiful new blue lake surrounded "
                    "by green hills, looking downward sorrowfully. Soft evening "
                    "light, mist rising from the still water, melancholic "
                    "atmosphere. Wide cinematic shot, vast peaceful lake "
                    "contrasting with sadness. Muted warm tones."
                ),
                "duration_hint": 20,
            },
        ],
    },
    # ------------------------------------------------------------------ #
    #  3. The Blue Jackal
    # ------------------------------------------------------------------ #
    "blue-jackal": {
        "title": "The Blue Jackal",
        "characters": {
            "jackal": (
                "A thin golden-brown Indian jackal with pointed triangular "
                "ears, a narrow snout, sharp amber eyes, a bushy tail with "
                "a dark tip, and visible ribs from hunger. Lean wiry build, "
                "coarse short fur with lighter tan on the underbelly."
            ),
            "jackal_blue": (
                "The same thin Indian jackal now entirely covered in bright "
                "indigo-blue dye — pointed triangular ears, narrow snout, "
                "bushy tail, all stained vivid blue. The dye coats every "
                "inch of fur, giving an unearthly otherworldly appearance."
            ),
        },
        "character_prompt": (
            "A thin golden-brown Indian jackal with pointed ears and a bushy "
            "tail standing next to the same jackal entirely covered in bright "
            "indigo-blue dye, side by side in a forest clearing. Full body "
            "view of both forms, bright daylight, photorealistic style."
        ),
        "narrator_intro": (
            "A jackal accidentally fell into a vat of blue dye and used his "
            "new appearance to declare himself king of the forest — until "
            "his true nature was revealed."
        ),
        "narrator_outro": (
            "The deception was shattered in an instant, and the false king "
            "fled into the night, never to return. The tale teaches us that "
            "no disguise can hide one's true nature forever."
        ),
        "scenes": [
            {
                "scene_number": 1,
                "description": "A hungry jackal enters a village at night",
                "narration": (
                    "There once lived a jackal so thin and hungry that his ribs "
                    "showed through his fur. Driven by desperate hunger, he "
                    "crept into a nearby village under the cover of darkness. "
                    "He hoped to find scraps of food, but danger lurked in "
                    "every shadow."
                ),
                "video_prompt": (
                    "A thin golden-brown Indian jackal with pointed ears and a "
                    "bushy dark-tipped tail sneaking through a dark Indian "
                    "village at night, slinking between mud-walled houses. "
                    "Flickering oil lamps cast orange pools of light. Tense "
                    "stealth atmosphere, deep shadows, the jackal's amber eyes "
                    "glowing. Low tracking shot following the jackal."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 2,
                "description": "Chased by dogs into a dyer's yard",
                "narration": (
                    "Suddenly, a pack of fierce village dogs caught his scent "
                    "and gave chase with furious barking. The terrified jackal "
                    "ran for his life through narrow lanes and winding alleys. "
                    "His heart hammered wildly as the snarling dogs closed in "
                    "on him from every direction."
                ),
                "video_prompt": (
                    "A thin golden-brown Indian jackal with pointed ears and a "
                    "bushy tail running at full speed through narrow village "
                    "lanes, pursued by a pack of snarling stray dogs. The "
                    "jackal leaps over a low wall into a courtyard filled with "
                    "large open vats of colorful dye. Motion blur, chaotic "
                    "energy, moonlight illuminating the chase."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 3,
                "description": "Falling into the blue dye vat",
                "narration": (
                    "In his blind panic, the jackal leaped over a wall and "
                    "tumbled headfirst into a large vat of indigo dye. He "
                    "thrashed and struggled in the thick blue liquid, certain "
                    "this was the end. When the dogs finally lost his scent, "
                    "an eerie silence fell over the yard."
                ),
                "video_prompt": (
                    "A thin golden-brown Indian jackal with pointed ears "
                    "mid-leap, splashing into a large clay vat filled with "
                    "vivid indigo-blue liquid dye. Dramatic splash sends blue "
                    "droplets arcing through the air. Slow-motion close-up of "
                    "the impact, blue dye erupting upward like a crown, "
                    "moonlight catching the droplets. Surreal and stunning."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 4,
                "description": "The jackal emerges completely blue",
                "narration": (
                    "The jackal crawled out of the vat at dawn, completely and "
                    "utterly transformed. Every inch of his fur was stained a "
                    "brilliant, unearthly shade of indigo blue. He caught his "
                    "reflection in a puddle and stared in disbelief — he was "
                    "unrecognizable, even to himself."
                ),
                "video_prompt": (
                    "A thin Indian jackal with pointed ears and a bushy tail, "
                    "now entirely covered in bright indigo-blue dye, climbing "
                    "out of a vat. It shakes off excess dye in slow motion, "
                    "blue droplets flying. The jackal stares at its own blue "
                    "paws in surprise. Dawn breaking on the horizon. Magical "
                    "transformation, ethereal blue glow on the fur."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 5,
                "description": "Forest animals are terrified",
                "narration": (
                    "When the blue jackal returned to the forest, every "
                    "creature that saw him fled in terror. No animal had ever "
                    "seen such a strange and magnificent beast before. The "
                    "deer, rabbits, and even the foxes scattered before this "
                    "mysterious blue apparition."
                ),
                "video_prompt": (
                    "A thin Indian jackal entirely covered in bright "
                    "indigo-blue dye with pointed ears and a bushy tail walks "
                    "confidently through a dense Indian forest as deer, "
                    "rabbits, foxes, and birds scatter in terror. Dramatic "
                    "low-angle shot of the blue jackal striding forward. "
                    "Shafts of sunlight through the canopy, dust particles, "
                    "awe and fear."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 6,
                "description": "The blue jackal declares himself king",
                "narration": (
                    "The jackal saw his chance and seized it with cunning "
                    "boldness. He announced in a deep voice that he had been "
                    "sent by the gods themselves to rule over all the animals. "
                    "The frightened creatures, including the mighty tiger and "
                    "elephant, bowed before their new king."
                ),
                "video_prompt": (
                    "A thin Indian jackal entirely covered in bright "
                    "indigo-blue dye standing regally on a large boulder in "
                    "a forest clearing, surrounded by bowing animals — "
                    "elephants, tigers, deer, peacocks all lowering their "
                    "heads. Majestic wide shot, golden sunlight streaming down "
                    "like a spotlight. Royal commanding atmosphere."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 7,
                "description": "Real jackals howl at the moon",
                "narration": (
                    "For many weeks, the blue jackal lived like a king, "
                    "feasting on the finest offerings. But one fateful night, "
                    "a pack of real jackals gathered on a nearby hill and began "
                    "howling at the full moon. Their wild, haunting chorus "
                    "echoed through the dark forest."
                ),
                "video_prompt": (
                    "A pack of thin golden-brown Indian jackals with pointed "
                    "ears and bushy tails howling at a large full moon on a "
                    "hilltop in the forest at night. Silhouettes sharp against "
                    "the bright silver moon. Hauntingly beautiful nocturnal "
                    "scene, deep blue night sky with stars, primal and wild "
                    "energy. Panoramic wide shot."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 8,
                "description": "The blue jackal howls back instinctively",
                "narration": (
                    "The sound stirred something deep within the blue jackal "
                    "that he could not control. Forgetting himself entirely, "
                    "he threw back his head and howled along with his own kind. "
                    "Every animal in the court turned to stare, recognizing "
                    "that unmistakable jackal's cry."
                ),
                "video_prompt": (
                    "A thin Indian jackal entirely covered in bright "
                    "indigo-blue dye on a boulder, head thrown back, howling "
                    "at the moon involuntarily. Surrounding animals — a tiger, "
                    "elephant, and deer — suddenly look up with shocked angry "
                    "expressions. Dramatic zoom on the blue jackal's open "
                    "mouth. Moonlight and tension, moment of revelation."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 9,
                "description": "The animals chase the imposter away",
                "narration": (
                    "The deception was shattered in an instant. Furious at "
                    "being fooled, the tiger roared and the elephant charged "
                    "toward the imposter. The terrified blue jackal fled into "
                    "the night with his false kingdom crumbling behind him, "
                    "never to return again."
                ),
                "video_prompt": (
                    "A thin Indian jackal covered in patchy indigo-blue dye "
                    "with golden-brown fur showing through running desperately "
                    "through a dark forest, chased by furious animals — a "
                    "tiger swiping, elephants trumpeting, birds diving. "
                    "Frantic chase sequence, dramatic camera movement, leaves "
                    "flying. Dark forest with dramatic moonlight shafts."
                ),
                "duration_hint": 20,
            },
        ],
    },
    # ------------------------------------------------------------------ #
    #  4. The Musical Donkey
    # ------------------------------------------------------------------ #
    "musical-donkey": {
        "title": "The Musical Donkey",
        "characters": {
            "donkey": (
                "A thin grey donkey with a white muzzle, large sad brown eyes, "
                "long drooping ears, and a distinctive dark cross-shaped marking "
                "running along its back and across its shoulders. Bony ribs "
                "slightly visible, short coarse grey fur, dark grey hooves."
            ),
            "jackal": (
                "A slender golden-brown jackal with large pointed ears, sharp "
                "amber eyes, a narrow snout with a black nose, and a long bushy "
                "tail tipped in black. Lean muscular build, tawny fur with "
                "lighter cream-colored underside."
            ),
        },
        "character_prompt": (
            "A thin grey donkey with a white muzzle and dark cross-marking on "
            "its back standing beside a slender golden-brown jackal with pointed "
            "ears and a bushy black-tipped tail, both in a moonlit cucumber "
            "field. Full body view, bright daylight, photorealistic style."
        ),
        "narrator_intro": (
            "In a small Indian village, a washerman's donkey toiled under the "
            "blazing sun by day and dreamed of freedom by night. One moonlit "
            "evening, that dream would lead him to a cucumber field, a jackal "
            "friend, and a very costly song."
        ),
        "narrator_outro": (
            "And so the donkey learned, with bruises and shame, that there is "
            "a time and place for everything. True wisdom lies not in silencing "
            "your voice forever, but in knowing when to speak and when to stay "
            "silent."
        ),
        "scenes": [
            {
                "scene_number": 1,
                "description": "The thin donkey working all day",
                "narration": (
                    "In a small village, a thin donkey belonged to a washerman "
                    "who worked him hard from dawn until dusk. The poor creature "
                    "carried heavy loads of laundry through the scorching heat "
                    "every single day. By evening, the donkey was always "
                    "exhausted and half-starved, dreaming of freedom."
                ),
                "video_prompt": (
                    "A thin grey donkey with a white muzzle and dark cross-marking "
                    "on its back carrying heavy bundles of laundry, walking along "
                    "a dusty village road under blazing midday sun. A washerman "
                    "walks beside it with a stick. Wide shot of the parched rural "
                    "Indian landscape, heat haze shimmering above the dirt road, "
                    "muted earth tones. Slow dolly tracking shot, empathy-evoking "
                    "pace. Photorealistic style."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 2,
                "description": "Donkey sneaks out at night",
                "narration": (
                    "Every night, once his master fell asleep, the clever donkey "
                    "would quietly slip out of his stable. He had discovered that "
                    "the darkness offered a freedom the daylight never could. "
                    "Under the cover of moonlight, he would set off in search of "
                    "food to fill his aching belly."
                ),
                "video_prompt": (
                    "A thin grey donkey with a white muzzle and dark cross-marking "
                    "on its back quietly stepping out of a simple mud stable into "
                    "a moonlit village night. The donkey walks cautiously past "
                    "sleeping thatched-roof houses toward open fields. Silver "
                    "moonlight on the dirt path, long blue shadows, stars "
                    "overhead. Medium tracking shot following the donkey from "
                    "behind. Peaceful nocturnal atmosphere, secretive mood."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 3,
                "description": "Meeting the jackal friend",
                "narration": (
                    "On one of these nightly adventures, the donkey befriended "
                    "a wild jackal who roamed the same fields. The jackal was "
                    "clever and cunning, and the two became unlikely companions. "
                    "Together they would explore the countryside, searching for "
                    "the best places to find a meal."
                ),
                "video_prompt": (
                    "A thin grey donkey with a white muzzle and dark cross-marking "
                    "meeting a slender golden-brown jackal with pointed ears and a "
                    "bushy black-tipped tail at the edge of a lush green cucumber "
                    "field under moonlight. They greet each other warmly, the "
                    "cucumber field stretching into the distance. Warm silver-blue "
                    "moonlight, fireflies floating in the air. Two-shot framing, "
                    "companionable atmosphere. Photorealistic style."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 4,
                "description": "Feasting in the cucumber field",
                "narration": (
                    "One night, the pair discovered a farmer's cucumber field "
                    "bursting with ripe, juicy cucumbers. They slipped through "
                    "the fence and began feasting greedily on the delicious "
                    "vegetables. Night after night they returned, eating their "
                    "fill until their bellies were round and satisfied."
                ),
                "video_prompt": (
                    "A thin grey donkey with a white muzzle and a slender "
                    "golden-brown jackal with pointed ears happily eating large "
                    "ripe cucumbers in a moonlit field. Rows of cucumber plants "
                    "surround them. The donkey munches contentedly, the jackal "
                    "nibbles delicately. Close-up intercut with wide shot of the "
                    "peaceful field. Cool blue-green night palette, sense of "
                    "plenty and contentment. Cinematic lighting."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 5,
                "description": "Donkey moved to sing by moonlight",
                "narration": (
                    "One particularly beautiful night, the full moon hung low "
                    "and luminous over the cucumber field. The donkey gazed up "
                    "at its silver glow and felt a powerful wave of emotion "
                    "swell inside his chest. He was so moved by the beauty of "
                    "the night that he felt an overwhelming urge to sing."
                ),
                "video_prompt": (
                    "A thin grey donkey with a white muzzle and dark cross-marking "
                    "standing in a cucumber field, gazing up dreamily at a "
                    "spectacularly large full moon. Ears perked forward, the moon "
                    "reflecting in the donkey's dark eyes. Romantic cinematic "
                    "lighting, soft lens flare from the moon, ethereal mist "
                    "hovering low over the field. Portrait-style close-up slowly "
                    "pulling back to reveal the moonlit landscape."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 6,
                "description": "Jackal warns against singing",
                "narration": (
                    "The jackal immediately sensed trouble and begged the donkey "
                    "not to make a sound. He warned his friend that a donkey's "
                    "bray would wake the farmer and bring nothing but disaster. "
                    "But the donkey was stubborn and proud, insisting that his "
                    "voice was a gift meant to be shared with the world."
                ),
                "video_prompt": (
                    "A slender golden-brown jackal with pointed ears and a bushy "
                    "tail urgently pawing at the leg of a thin grey donkey with a "
                    "white muzzle, shaking its head in warning. The donkey looks "
                    "stubborn, chin raised defiantly. Moonlit cucumber field, "
                    "split framing showing the jackal's worried face and the "
                    "donkey's proud posture. Dramatic shadow play, building "
                    "tension. Cinematic two-shot."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 7,
                "description": "Donkey brays loudly",
                "narration": (
                    "Ignoring every word of warning, the donkey threw back his "
                    "head and let out the loudest, most terrible bray he could "
                    "muster. The horrible sound shattered the peaceful silence "
                    "of the night and echoed across the fields. The wise jackal "
                    "did not wait — he turned and ran as fast as his legs could "
                    "carry him."
                ),
                "video_prompt": (
                    "A thin grey donkey with a white muzzle and dark cross-marking "
                    "head thrown back, mouth wide open, braying loudly at the full "
                    "moon in a cucumber field. Sound waves visually ripple outward "
                    "through the night air. Birds scatter from nearby trees. A "
                    "slender golden-brown jackal sprints away in the background. "
                    "Dramatic slow-motion, powerful moonlit silhouette, comedic "
                    "yet dramatic energy. Wide cinematic shot."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 8,
                "description": "Farmer wakes and beats the donkey",
                "narration": (
                    "The farmer jolted awake at the dreadful noise and grabbed "
                    "his heaviest stick. He stormed into the cucumber field and "
                    "found the donkey standing among his trampled crops. In a "
                    "fury, he beat the foolish donkey so badly that the poor "
                    "creature could barely stand."
                ),
                "video_prompt": (
                    "An angry Indian farmer with a wooden stick running through "
                    "a moonlit cucumber field toward a startled thin grey donkey "
                    "with a white muzzle. Trampled cucumber plants everywhere. "
                    "The farmer swings the stick. Night scene lit by a swinging "
                    "lantern casting dramatic dancing shadows. Chaotic action, "
                    "the donkey cowering and trying to flee. Handheld camera "
                    "energy, consequence and regret."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 9,
                "description": "Moral — bruised donkey limps home",
                "narration": (
                    "At dawn, the bruised and battered donkey limped slowly back "
                    "toward the village, every step a painful reminder of his "
                    "foolishness. The jackal watched from a distance and shook "
                    "his head sadly. The donkey had learned too late that there "
                    "is a time and place for everything — and wisdom lies in "
                    "knowing the difference."
                ),
                "video_prompt": (
                    "A bruised thin grey donkey with a white muzzle limping "
                    "slowly along a village path at dawn, head hanging low, "
                    "welts visible on its hide. A slender golden-brown jackal "
                    "with pointed ears watches from behind a bush with a knowing "
                    "expression. Pink and orange sunrise on the horizon, long "
                    "morning shadows. Melancholic wide shot, quiet reflective "
                    "cinematic atmosphere. Slow dolly pull-back."
                ),
                "duration_hint": 20,
            },
        ],
    },
    # ------------------------------------------------------------------ #
    #  5. The Loyal Mongoose
    # ------------------------------------------------------------------ #
    "loyal-mongoose": {
        "title": "The Loyal Mongoose",
        "characters": {
            "mongoose": (
                "A small reddish-brown Indian mongoose with a bushy striped "
                "tail banded in dark brown and cream, alert dark eyes, a "
                "pointed pink nose, short rounded ears, and wiry coarse fur. "
                "Compact muscular body low to the ground, quick and agile."
            ),
            "mother": (
                "A young Indian woman with long black hair in a braid, warm "
                "brown skin, wearing a bright red sari with intricate gold "
                "embroidery along the border. Slender build, a gold nose ring, "
                "and thin gold bangles on her wrists."
            ),
            "cobra": (
                "A large black king cobra with glossy dark scales, a broad "
                "pale yellowish-white hood marked with faint spectacle "
                "patterns, piercing dark eyes, and a forked black tongue. "
                "Over five feet long with a thick muscular body."
            ),
        },
        "character_prompt": (
            "A small reddish-brown Indian mongoose with a bushy striped tail "
            "standing protectively beside a young Indian woman in a red and "
            "gold sari, with a large black king cobra with a pale hood coiled "
            "nearby. All three in a sunlit Indian village courtyard. Full body "
            "view, bright daylight, photorealistic style."
        ),
        "narrator_intro": (
            "In a peaceful Indian village, a farmer's family raised a mongoose "
            "alongside their newborn son, loving it like a second child. But "
            "one fateful afternoon, loyalty and love would collide with fear "
            "and haste, leaving behind a lesson no mother could ever forget."
        ),
        "narrator_outro": (
            "The mother wept over the loyal mongoose who had given its life to "
            "protect her child. She had acted in haste and repented at leisure. "
            "This tale reminds us to never judge before knowing the full truth, "
            "for a moment of blind rage can destroy what years of love have built."
        ),
        "scenes": [
            {
                "scene_number": 1,
                "description": "Happy family with baby and mongoose",
                "narration": (
                    "In a peaceful Indian village, a farmer and his wife lived "
                    "happily with their newborn baby boy. They also kept a young "
                    "mongoose as a pet, raising it alongside their child like a "
                    "second son. The mongoose and the baby grew up together, "
                    "sharing the same cradle and the same love."
                ),
                "video_prompt": (
                    "Inside a cozy Indian village home, a young Indian woman in "
                    "a red and gold sari and her husband smiling over their baby "
                    "in a wooden cradle. A small reddish-brown mongoose with a "
                    "bushy striped tail curls up beside the cradle protectively. "
                    "Warm oil-lamp lighting, earthen walls, colorful textiles. "
                    "Intimate domestic scene. Close-up on the mongoose nuzzling "
                    "the sleeping baby. Photorealistic style."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 2,
                "description": "Mother leaves mongoose to guard baby",
                "narration": (
                    "One morning, the mother needed to fetch water from the well "
                    "and could not take the baby with her. She looked at the "
                    "mongoose, who sat alert and watchful beside the cradle, and "
                    "felt reassured. Trusting the loyal creature to guard her "
                    "sleeping child, she placed the water pot on her head and left."
                ),
                "video_prompt": (
                    "A young Indian woman in a red and gold sari stepping out of "
                    "a village house carrying a clay water pot on her head, looking "
                    "back at a small reddish-brown mongoose with a bushy striped "
                    "tail sitting alertly beside a baby's wooden cradle in the "
                    "doorway. Bright morning sunlight outside contrasts with the "
                    "shaded interior. Split lighting between warm interior and "
                    "bright exterior. Medium shot, photorealistic style."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 3,
                "description": "Cobra enters the house",
                "narration": (
                    "While the mother was away, a deadly black cobra slithered "
                    "silently through a crack in the mud wall. The venomous "
                    "snake moved toward the cradle where the helpless baby lay "
                    "sleeping. The mongoose spotted the intruder immediately and "
                    "bristled with fury, ready to defend the child with its life."
                ),
                "video_prompt": (
                    "A large black king cobra with a pale yellowish-white hood "
                    "slithering silently through a gap in the mud wall of an "
                    "Indian village house, moving toward a baby's wooden cradle. "
                    "The cobra's hood spreads wide. Low-angle floor-level shot "
                    "following the snake. Ominous shadow on the wall, tense "
                    "atmosphere, dim interior with a single ray of light from "
                    "the doorway. Cinematic suspense lighting."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 4,
                "description": "Mongoose fights the cobra",
                "narration": (
                    "The mongoose launched itself at the cobra with fearless "
                    "determination, and a vicious battle erupted on the earthen "
                    "floor. The cobra struck again and again with its deadly "
                    "fangs, but the mongoose was too quick, dodging every attack. "
                    "They fought with terrible ferocity while the baby slept on "
                    "unaware."
                ),
                "video_prompt": (
                    "An intense battle between a small reddish-brown mongoose "
                    "with a bushy striped tail and a large black king cobra with "
                    "a pale hood inside a village house. The mongoose dodges the "
                    "cobra's strikes with lightning speed, fur bristling. Dust "
                    "rising from the earthen floor, baby's cradle in the "
                    "background. Dynamic close-up action, high-energy fight "
                    "choreography. Multiple rapid camera angles."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 5,
                "description": "Mongoose defeats the cobra",
                "narration": (
                    "After a fierce and desperate struggle, the brave little "
                    "mongoose finally sank its teeth into the cobra's neck and "
                    "held on tight. The great snake thrashed and writhed but "
                    "could not break free. At last the cobra went limp, and the "
                    "mongoose stood victorious, panting with exhaustion."
                ),
                "video_prompt": (
                    "A small reddish-brown mongoose with a bushy striped tail "
                    "standing victorious over a dead large black king cobra on "
                    "the floor of a village house. Blood on the mongoose's mouth "
                    "and paws. The baby sleeps peacefully in the cradle behind. "
                    "A shaft of sunlight illuminating the scene like a spotlight. "
                    "Heroic composition, still and powerful moment. Slow push-in "
                    "on the mongoose. Photorealistic style."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 6,
                "description": "Mongoose runs to greet returning mother",
                "narration": (
                    "When the mongoose heard the mother's footsteps approaching "
                    "the house, it rushed to the doorway to greet her. Its little "
                    "heart swelled with pride, eager to show her what it had done. "
                    "It ran toward her happily, not realizing that its mouth and "
                    "paws were still covered in the cobra's blood."
                ),
                "video_prompt": (
                    "A small reddish-brown mongoose with a bushy striped tail "
                    "and blood-stained paws running excitedly toward the open "
                    "doorway of a village house where a young Indian woman in a "
                    "red and gold sari is arriving with a water pot. The mongoose "
                    "looks happy and proud. Bright exterior light flooding through "
                    "the doorway, the bloodied appearance contrasting with joyful "
                    "demeanor. Dramatic irony. Medium shot."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 7,
                "description": "Mother sees blood and strikes mongoose",
                "narration": (
                    "The mother looked down and saw the mongoose drenched in "
                    "blood, and a terrible thought seized her heart. She was "
                    "certain the creature had attacked her baby. Blinded by rage "
                    "and terror, she swung her heavy water pot down upon the "
                    "mongoose with all her strength."
                ),
                "video_prompt": (
                    "A young Indian woman in a red and gold sari dropping a clay "
                    "water pot that shatters on the ground, face twisted in "
                    "horror and rage. She strikes downward with the heavy pot "
                    "toward a small reddish-brown mongoose with blood-stained "
                    "fur at her feet. Slow-motion shot of the pot breaking, "
                    "water splashing, the tragic moment of misunderstanding. "
                    "Dramatic lighting, emotional devastation. Close-up."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 8,
                "description": "Mother discovers dead cobra and safe baby",
                "narration": (
                    "The mother rushed inside, trembling with dread, but found "
                    "her baby sleeping peacefully in the cradle. Then she saw "
                    "the dead cobra lying on the floor, its body torn apart by "
                    "the brave mongoose. The horrible truth crashed over her "
                    "like a wave — the mongoose had saved her child's life."
                ),
                "video_prompt": (
                    "A young Indian woman in a red and gold sari inside a village "
                    "house, hands covering her mouth in shock, staring at a dead "
                    "large black king cobra on the floor near her baby's cradle. "
                    "The baby sleeps peacefully. Tears stream down her face. "
                    "Camera slowly pans from the dead snake to the sleeping baby "
                    "to the woman's devastated expression. Gut-wrenching "
                    "realization. Cinematic push-in."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 9,
                "description": "Moral — grief and regret",
                "narration": (
                    "The mother ran back outside and gathered the lifeless "
                    "mongoose into her arms, weeping with unbearable grief. She "
                    "had killed the most loyal friend her family ever had, all "
                    "because she acted without thinking. This is the tragedy of "
                    "hasty judgment — once done, it can never be undone."
                ),
                "video_prompt": (
                    "A young Indian woman in a red and gold sari kneeling on "
                    "the ground outside her village house at sunset, cradling "
                    "a small lifeless reddish-brown mongoose with a bushy "
                    "striped tail in her arms, weeping. The setting sun casts "
                    "long golden shadows. Baby's cradle visible through the "
                    "open door behind her. Devastating wide shot, silhouette "
                    "against the sunset. Cinematic golden-hour tragedy."
                ),
                "duration_hint": 20,
            },
        ],
    },
    # ------------------------------------------------------------------ #
    #  6. The Brahmin and the Goat
    # ------------------------------------------------------------------ #
    "brahmin-and-goat": {
        "title": "The Brahmin and the Goat",
        "characters": {
            "brahmin": (
                "An elderly Indian Brahmin with deep brown wrinkled skin, a "
                "long grey beard, a white cotton dhoti and matching shawl "
                "draped over one shoulder, a red tilak mark on his forehead, "
                "and a tall wooden walking staff. Thin build, bare feet in "
                "simple leather sandals."
            ),
            "goat": (
                "A healthy medium-sized white goat with a distinctive brown "
                "patch on its forehead shaped like a thumbprint, short curved "
                "horns, a small beard, bright yellow-green eyes, and a rope "
                "halter around its neck. Clean white fur, sturdy legs."
            ),
            "thieves": (
                "Three scruffy-looking Indian men in torn and patched brown "
                "clothing, each with unkempt black hair and stubble. The first "
                "is tall and lanky, the second is short and stocky, and the "
                "third is of medium build with a scar across his left cheek."
            ),
        },
        "character_prompt": (
            "An elderly Indian Brahmin in a white dhoti with a grey beard and "
            "wooden walking staff, standing beside a healthy white goat with "
            "a brown patch on its forehead, while three scruffy-looking thieves "
            "in torn brown clothing lurk behind nearby trees. Forest path "
            "setting. Full body view, bright daylight, photorealistic style."
        ),
        "narrator_intro": (
            "A kind and trusting Brahmin was given a fine goat as a gift and "
            "set off for home through the forest. But three cunning thieves "
            "had spotted him, and with nothing but clever words, they would "
            "rob him of his prize and his good sense."
        ),
        "narrator_outro": (
            "The poor Brahmin lost his goat not to strength or violence, but "
            "to the power of repeated lies. This tale teaches us that a person "
            "who does not trust their own eyes and judgment can be made to "
            "believe anything — no matter how absurd."
        ),
        "scenes": [
            {
                "scene_number": 1,
                "description": "Brahmin receives goat as a gift",
                "narration": (
                    "An elderly Brahmin was gifted a fine, healthy goat by a "
                    "grateful villager after performing a sacred ceremony. The "
                    "old man was delighted, for the goat would be a worthy "
                    "offering at the temple. He thanked the villager warmly and "
                    "set off on the long forest road toward home."
                ),
                "video_prompt": (
                    "An elderly Indian Brahmin in a white dhoti with a grey "
                    "beard receiving a healthy white goat with a brown patch on "
                    "its forehead, tied with a rope, from a village elder in a "
                    "rural courtyard. Both men smile warmly. Bright morning "
                    "light, thatched-roof houses in the background. Warm earth "
                    "tones, ceremonial mood. Medium shot of the handover moment. "
                    "Photorealistic style."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 2,
                "description": "Brahmin carries goat on forest path",
                "narration": (
                    "The Brahmin hoisted the goat across his shoulders and began "
                    "walking through the dense forest. The path was long and "
                    "lonely, winding through tall trees and thick undergrowth. "
                    "He walked steadily, humming a prayer to himself, unaware "
                    "that three cunning thieves had been watching him from the "
                    "shadows."
                ),
                "video_prompt": (
                    "An elderly Indian Brahmin in a white dhoti with a grey "
                    "beard and wooden walking staff walking along a narrow "
                    "forest path with a healthy white goat with a brown forehead "
                    "patch slung across his shoulders. Dense Indian forest on "
                    "both sides, dappled sunlight on the path. Long tracking "
                    "shot from behind, gradually revealing the depth of the "
                    "shadowy forest. Serene atmosphere."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 3,
                "description": "First thief says it is a dog",
                "narration": (
                    "The first thief stepped onto the path and greeted the "
                    "Brahmin with mock surprise. He pointed at the goat and "
                    "asked why a holy man was carrying a dirty dog on his "
                    "shoulders. The Brahmin laughed and replied that the man "
                    "must be blind, for it was clearly a goat."
                ),
                "video_prompt": (
                    "A tall lanky man in torn brown clothing stepping out from "
                    "behind a tree on a forest path, confronting an elderly "
                    "Indian Brahmin in a white dhoti carrying a healthy white "
                    "goat with a brown forehead patch. The thief points at the "
                    "goat with an exaggerated shocked expression. The Brahmin "
                    "looks confused. Dramatic forest lighting with deep shadows, "
                    "the thief partially in shadow. Medium two-shot."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 4,
                "description": "Second thief repeats the trick",
                "narration": (
                    "A little further down the path, the second thief appeared "
                    "and stared at the Brahmin in disbelief. He too asked why "
                    "the Brahmin was carrying a dog, shaking his head with pity. "
                    "A seed of doubt began to take root in the old man's mind, "
                    "though he kept walking."
                ),
                "video_prompt": (
                    "A short stocky man in torn brown clothing appearing on the "
                    "forest path, gesturing at the white goat with a brown "
                    "forehead patch on an elderly Brahmin's shoulders with a "
                    "look of disgust. The Brahmin in a white dhoti appears "
                    "worried, examining the goat more closely. Deeper in the "
                    "forest, darker lighting, growing doubt conveyed through "
                    "body language. Tighter framing, cinematic tension."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 5,
                "description": "Third thief convinces the Brahmin",
                "narration": (
                    "When the third thief appeared and said the very same thing, "
                    "the Brahmin's confidence shattered completely. Three "
                    "strangers could not all be wrong — perhaps he truly had "
                    "been given a dog instead of a goat. Panic and confusion "
                    "overwhelmed the old man, and he began to tremble with fear."
                ),
                "video_prompt": (
                    "A medium-built man with a scar on his left cheek in torn "
                    "brown clothing on the path, pointing and laughing at an "
                    "elderly Brahmin in a white dhoti carrying a white goat "
                    "with a brown forehead patch. The Brahmin looks panicked "
                    "and distressed, setting the goat down on the path hastily. "
                    "Darkest part of the forest, claustrophobic framing, "
                    "psychological pressure visible on the Brahmin's face."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 6,
                "description": "Brahmin abandons goat and flees",
                "narration": (
                    "In a moment of blind fear, the Brahmin flung the goat off "
                    "his shoulders and ran down the path as fast as his old legs "
                    "would carry him. He was convinced he had been carrying some "
                    "cursed creature all along. The poor goat stood alone on the "
                    "forest path, watching its master disappear into the trees."
                ),
                "video_prompt": (
                    "An elderly Brahmin in a white dhoti with a grey beard "
                    "running away down a forest path in fear, leaving a healthy "
                    "white goat with a brown forehead patch standing alone "
                    "behind him. The goat watches him go with a calm expression. "
                    "Wide shot showing the growing distance between them. Ironic "
                    "sunlight breaking through the canopy onto the perfectly "
                    "normal goat. Comic tragedy, absurdity of the moment."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 7,
                "description": "Three thieves steal the goat",
                "narration": (
                    "The three thieves emerged from their hiding places, laughing "
                    "and congratulating each other on their brilliant scheme. "
                    "They gathered around the bewildered goat and led it away "
                    "into the forest. Without lifting a finger in violence, they "
                    "had stolen the Brahmin's prize through nothing but clever "
                    "words."
                ),
                "video_prompt": (
                    "Three scruffy men in torn brown clothing — one tall and "
                    "lanky, one short and stocky, one with a scarred cheek — "
                    "emerging from the forest shadows and surrounding the "
                    "abandoned white goat with a brown forehead patch on the "
                    "path. They high-five and laugh, one picking up the goat's "
                    "rope. Devious expressions, dark forest backdrop with a "
                    "shaft of light. Medium group shot, triumphant villainy."
                ),
                "duration_hint": 20,
            },
            {
                "scene_number": 8,
                "description": "Moral — Brahmin realizes his mistake",
                "narration": (
                    "When the Brahmin finally stopped to catch his breath, the "
                    "truth slowly dawned upon him. There had been no dog — only "
                    "a goat and three liars who had robbed him of his own good "
                    "sense. He learned that day that a person who does not trust "
                    "their own eyes can be made to believe anything."
                ),
                "video_prompt": (
                    "An elderly Indian Brahmin in a white dhoti with a grey "
                    "beard sitting alone on a rock at the edge of the forest "
                    "at sunset, head in his hands in regret. His wooden walking "
                    "staff leans against the rock. The empty road stretches "
                    "behind him. Orange and purple sunset sky, long shadows. "
                    "Melancholic wide shot, slow dolly pull-back. Cinematic "
                    "golden-hour reflection."
                ),
                "duration_hint": 20,
            },
        ],
    },
}


def get_story(slug: str) -> dict | None:
    """Return a story dict by slug, or None if not found."""
    return STORIES.get(slug)


def list_stories() -> list[tuple[str, str]]:
    """Return a list of (slug, title) for all available stories."""
    return [(slug, story["title"]) for slug, story in STORIES.items()]
