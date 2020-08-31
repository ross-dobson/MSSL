import pathlib  # used for compatibility with non-POSIX systems
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import datetime
# remember to run 'matplotlib tk' in the interpreter

from sklearn import linear_model
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score

from SolarWindImport import import_omni_year, import_omni_month


def main():

    # ---------------------------------------------------------------
    # IMPORTING THE DATA

    # The method import_omni_year checks for Pickles itself
    # so we do not need to enclose this in a try statement
    year = 2003
    data_2003 = import_omni_year(year)

    # ---------------------------------------------------------------
    # IMPORTING OCTOBER AND NOVEMBER SEPERATELY TO ZOOM IN

    # pkl_dir = pathlib.Path('Data/OMNI/pickles')
    # oct_nov_pkl_path = pkl_dir / 'oct_nov_2003.pkl'

    # try:
    #     df_oct_nov_2003 = pd.read_pickle((oct_nov_pkl_path))
    #     print("Found the pickle for October and November 2003.")

    # except FileNotFoundError:
    #     print("Couldn't find the pickle for October and November 2003."
    #           + "-> Generating one from the .asc files.")

    #     print('Creating local directory at ', pkl_dir,
    #           ' (if it doesn\'t already exist):')
    #     pathlib.Path(pkl_dir).mkdir(exist_ok=True)
    #     print("Done. Importing the data for October and November.")

    #     df_oct_2003 = import_omni_month(2003, 10)
    #     df_nov_2003 = import_omni_month(2003, 11)
    #     df_oct_nov_2003 = pd.concat([df_oct_2003, df_nov_2003])
    #     df_oct_nov_2003.to_pickle(oct_nov_pkl_path)  # store for future use

    print("All 2003 data has been loaded.")
    # print("\n2003 data:")
    # print(data_2003)

    # ---------------------------------------------------------------
    # PLOTTING THE PARAMETERS

    plot_vals = ['B_X_GSM', 'B_Y_GSM', 'B_Z_GSM', 'n_p', 'AL', 'P', 'V']
    # for val in plot_vals:
    #     year_title = str(val) + ' in ' + str(year)
    #     df_2003.plot(x='DateTime', y=val, title=year_title)

    #     oct_nov_title = str(val) + ' in October and November 2003'
    #     df_oct_nov_2003.plot(x='DateTime', y=val, title=oct_nov_title)

    # ---------------------------------------------------------------
    # CORRELATION MATRIX BEFORE SCALER

    print("\nCorrelation matrix before standardization:\n")
    corr_2003 = data_2003[plot_vals].corr()
    print(corr_2003)

    # print("\nCorrelation matrix for October & November 2003\n")
    # corr_oct_nov_2003 = df_oct_nov_2003[plot_vals].corr()
    # print(corr_oct_nov_2003)

    # ---------------------------------------------------------------
    # SCALER/TRANSFORMING THE DATA

    # The features we care about
    model_vals = ['B_X_GSM', 'B_Y_GSM', 'B_Z_GSM', 'n_p', 'P', 'V']

    # get just that data
    df_2003 = data_2003[model_vals]
    df_2003_cols = df_2003.columns  # column labels
    df_2003_index = df_2003.index  # row labels

    df_AL = data_2003['AL']
    df_AL_index = df_AL.index  # should be same as df anyway, just datetimes

    # scale the main features
    scaler = StandardScaler()
    scaler = scaler.fit(df_2003)
    arr_2003_scaled = scaler.transform(df_2003)

    # need to add it back into a DF
    df_2003 = pd.DataFrame(arr_2003_scaled,
                           columns=df_2003_cols, index=df_2003_index)
    # print("\nDF 2003 after scaling:\n")
    # print(df_2003)

    # scale AL
    scaler2 = StandardScaler()
    arr_AL = df_AL.to_numpy()
    arr_AL = arr_AL.reshape(-1, 1)
    scaler2 = scaler2.fit(arr_AL)
    arr_AL_scaled = scaler2.transform(arr_AL)

    # need to add it back into a DF
    df_AL = pd.DataFrame(arr_AL_scaled, columns=['AL'], index=df_AL_index)
    # print("\nAL after scaling\n")
    # print(df_AL)

    # ---------------------------------------------------------------
    # CORR AFTER STANDARDISATION
    df_2003.insert(4, "AL", arr_AL_scaled)
    print("\nCorr after standardization:\n")
    print(df_2003.corr())

    # ---------------------------------------------------------------
    # REMOVING USELESS PARAMETERS
    # TODO: formally investigate mutual information?

    # removing n_p - in the words of Mayur
    # "by far weakest correlation with AL and a strong correlation with P"
    df_2003 = df_2003.drop(["n_p"], axis=1)
    # ---------------------------------------------------------------
    # INTERPOLATING GAPS
    # resample the data into one minute chunks

    # just a failsafe, ensure everything is 1 minutes apart
    df_resampled = df_2003.resample(
        '1T', loffset=datetime.timedelta(seconds=30.)).mean()
    df_2003 = df_resampled.interpolate(method='linear', limit=15)
    # I've tested, dropna does work. Can use np.isnan on each value to check

    # ---------------------------------------------------------------
    # REMOVING NaN VALUES
    # go by rows, delete if ANY values are NaN, do this in same df
    df_2003.dropna(axis='index', how='any', inplace=True)
    # to check this has worked, notice the last 30 minutes on Dec 31 are gone.
    # previously, these were riddled with NaNs.

    # ---------------------------------------------------------------
    # PLOT HISTOGRAMS:

    # hist_dir = pathlib.Path('Figures')
    # pathlib.Path(hist_dir).mkdir(exist_ok=True)

    # for i, param in enumerate(plot_vals):
    #     plt.figure()
    #     plt.hist(df_2003[param], bins=35)
    #     plt.title('Histogram of '+param+' after StandardScaler')

    # ---------------------------------------------------------------
    # DISCRETIZE AL
    df_AL = df_2003['AL'].copy()

    # Roll right, 30 minutes.
    # E.g. 12:00-12:30 -> 12:30, 12:01-12:31 -> 12:31
    discrete_AL = df_AL.rolling(30).min()

    # now, because this isn't a native argument, we roll left by shifting
    discrete_AL = discrete_AL.shift(-30)

    # ---------------------------------------------------------------
    # TRAIN TEST SPLIT

    # Needs shape (n_samples, n_features) -> 525600 samples
    # Split the data into two parts, one for training and testing
    print(df_2003)
    print(discrete_AL)

    # 60% of data for training, 40% of data held back for testing
    X_train, X_test, y_train, y_test = train_test_split(
        df_2003, discrete_AL, test_size=0.4, random_state=47)

    # ---------------------------------------------------------------
    # LINEAR REGRESSION
    # create the linear regression object
    # regr = linear_model.LinearRegression()

    # # train it
    # regr.fit(X_train, y_train)

    # cross-validation
    # scores = cross_val_score(regr, X_train, y_train, cv=10)
    # print(scores)


main()
