# FactorioInformationExtractor

Information Extractor for use with the Archipelago Cross-Game Randomizer.  
Adds the command "/ap-get-info-dump" to create the required exports in script-output.  
Those files then belong in <AP>/worlds/factorio/data  
You can find us at https://discord.com/invite/8Z65BR2 or https://archipelago.gg  

## Run the extractor from a terminal

The helper script starts Factorio headlessly, creates a temporary map (or loads
an existing save), and runs `/ap-get-info-dump` over RCON:

```sh
python3 scripts/run-info-dump.py --factorio /path/to/factorio
```

To load an installed modpack, pass its Factorio `mods` directory. The script
temporarily stages that mod directory and enables this extractor without
changing the installed files:

```sh
python3 scripts/run-info-dump.py \
  --factorio /path/to/factorio \
  --mods ~/.factorio/mods \
  --save /path/to/factorio/saves/my-save.zip
```

The Factorio config can be selected with `--config`. The exported JSON files
are written to the `script-output` directory under Factorio's configured
write-data path.

If no `mod-list.json` exists and `--disable-space-age` is set,
the runner uses the bundled [mod-list.json](scripts/mod-list.json) with Space
Age and its related expansions disabled. An existing mod list takes
precedence and is left unchanged:

```sh
python3 scripts/run-info-dump.py \
  --factorio /path/to/factorio \
  --disable-space-age
```

## Build mod archives

Build both Factorio targets into `./build`:

```sh
python3 scripts/build.py
```

Pass one or more targets to build only those archives:

```sh
python3 scripts/build.py 2.0
python3 scripts/build.py 2.0 2.1
```

The ZIPs use Factorio-compatible names, with target-specific mod versions
derived from the source patch version. For example, source version `2.1.1`
produces `modded-archipelago-extractor_2.0.1.zip` and
`modded-archipelago-extractor_2.1.1.zip`. Each archive contains the matching
`factorio_version`; the source `info.json` is not modified.
