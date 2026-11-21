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
