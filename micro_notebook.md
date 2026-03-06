# Amanita microscopy analyzation

## Organization of microscopy data
It's time to normalize the microscopy data to start analyzing the data and creating summary figures.

The main thing to note, is we are also aggregating the data so that the values that will be used are min, max, 10th, and 90th percentile. This is the data that will ultimately be displayed in the database but, we will have all the data and can go back to it to create figures if we deem necessary

The first step, I manually made an excel sheet for basidiospore data in normailzed format and manually entered the first two specimens to give AI a better idea of how I want the data set up.

I then took the next two specimens in original form and copied them into their own workbook called 'training_data' I will use this to see if AI does what I want it to do without it doing it for all of the sheets.

Then I prompted it with this:
"I have a mission for you. I have started how I want the data for basidiospores to be organized. I have columns listed for length width and q value (min=minimum, 10=10th percentile, 90=90th percentile, max=maximum) I want you to take the training_book sheet I give you and write me a script that takes the data from it and maps it to the basidiospore data book. I want you to make it a loop because my actual excel sheet that looks like the training_book is set up the same but has many more specimens each with their own sheet. Show me your steps so I can record them."

Before running the script it gave me, I want to create a virtual environment with python to keep any packages I install localized to this project. This helps reduce dependency issues throughout the computer

```zsh
cd ~/Desktop/wiscam_microscopy #Moves me into the micrscopy folder
conda create -n micro_env #Creates an isolated environment that I named (-n) micro_env
conda activate micro_env #activates micro_env you can check it worked as the command line should show (micro_env) at the beginning
```

Now that I have the environment created and activated, I can download all of the packages needed to executed this project

```zsh 
pip install pandas
pip install numpy #These are two commonly used packages you will likely become familiar with if you stick with it
pip install pathlib
pip install openpyxl
#All of these packages are found at the top of the python script we are going to use "map_spores.py". You will see two of the imported packages we didn't install because they come preinstalled with conda (math, re)
```

Now we have our needed packages we can execute the script and see if it does what we want

```zsh
cd data
cp training_book.xlsx normalized #copies training data into the normalized folder where the basidiospore.xlsx is found
```

Now that the two excel sheets are in the same folder as our python script we can execute the script

```zsh
cd normalized
python3 map_spores.py
```

Of course, this takes a few iterations to hone in on getting the AI to produce a script that executes exactly what is wanted. I only have the iteration that does what I want. The process of getting to the wanted script is irrelevant so is not recorded.

I'm now happy with the script so I am making a copy of 'basidiospore.xlsx' and then deleteing all data input. I am going to add the full 'amanita_microscopy.xlsx' workbook and modify the script to run ^ as the map and put the data into the empty 'basidiospore.xlsx' workbook.

```zsh
cd ./data
cp amanita_microscopy.xlsx normalized
#edit map_spores.py to make sure it is locating all the correct .xlsx sheets
python3 map_spores.py
```
basidiospore_filled.xlsx is looking mighty dandy

Now moving onto basidia and I'm using a similar work flow just shifting it to fit the basidia side of the work book.

The AI has good practice with the basidiospore data at this point so hoping it's a quicker process.

Yeah that was 10x as fast. It populated it perfectly and now I want to inspect the basidia data to see where there are gaps and what needs to be filled in.

```zsh
cd data/normalized
python3 map_basidia.py
```


I am going to use R to learn a bit more about what this data is saying. Find the work at 'mh_basid.rmd'