# CLPC
CafeLoader Project Compiler, following the WUAPPS standard.  
An example project can be found [here](https://github.com/aboood40091/NSMBU-Haxx-Rewrite).  

## Usage
You will need the tools below to build projects using this program:

- [MULTI GreenHills Software](http://letmegooglethat.com/?q=%22MULTI-5_3_27%22)
- [wiiurpxtool](https://github.com/0CBH0/wiiurpxtool/releases)

Then you either set their path in `main.py` or you can add these to your environment variables:

```env
CLPC_GHS_DIR=C:/<ghs_install_dir>/ghs/multi327
CLPC_WIIURPXTOOL_PATH=C:/<any_dir>/wiiurpxtool.exe
```

- Now simply run:

```shell
python ./src/main.py
```

You will be prompted to enter the path to your ``project.yaml`` file.

- Alternatively you can also run:

```shell
python ./src/main.py <path_to_your_project_yaml>
```
