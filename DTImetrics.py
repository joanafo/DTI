#Función para calcular las metricas: FA, DM, RD, AD de una imagen DTI
import os
import sys
import numpy as np
import argparse


def DTImetrics(input_filename, output_filename, bvec_filename, bval_filename, direction, inputT1_filename, no_tracks, view=False):

    if view:
        print('TRUE')
        if direction == "AP-PA":
            for filename in os.listdir("."):
                #Conversion nifti2mif de la imagen AP
                if filename.endswith("AP_dwi.nii.gz"):
                    print('inside file')
                    basename = os.path.splitext(filename)[0][:-3]
                    mif_filename = f"dwi_{output_filename}.mif"
                    
                    os.system(f"mrconvert {filename} {mif_filename} -fslgrad {bvec_filename} {bval_filename}")
                    os.system(f"mrview {mif_filename}")

                    #denoise
                    den_filename = f"dwi_den_{output_filename}.mif"
                    os.system(f"dwidenoise {mif_filename} {den_filename} -noise noise.mif")
                    os.system(f"mrview {den_filename}")
                    meanap_filename = "mean_b0_AP.mif"
                    os.system(f"dwiextract {den_filename} - -bzero | mrmath - mean {meanap_filename} -axis 3")

                if filename.endswith("PA_dwi.nii.gz"):
                    basename = os.path.splitext(filename)[0][:-3]
                    bvecpa_filename = basename + "bvec"
                    bvalpa_filename = basename + "bval"
                    mifpa_filename = "PA.mif"
                    os.system(f"mrconvert {filename} {mifpa_filename}")
                    meanpa_filename = "mean_b0_PA.mif"
                    os.system(f"mrconvert {mifpa_filename} -fslgrad {bvecpa_filename} {bvalpa_filename} - | mrmath - mean {meanpa_filename} -axis 3")

            b0_filename = "b0_pair" + ".mif"
            os.system(f"mrcat {meanap_filename} {meanpa_filename} -axis 3 {b0_filename}")
            #Eddy current
            preproc_filename = f"dwi_den_eddy_{output_filename}.mif"
            os.system(f"dwifslpreproc {den_filename} {preproc_filename} -nocleanup -pe_dir AP -rpe_pair -se_epi {b0_filename} -eddy_options \" --slm=linear --data_is_shelled\"")
            os.system(f"mrview {preproc_filename}")
            #bias
            bias_filename = f"dwi_den_eddy_bias_{output_filename}.mif"
            os.system(f"dwibiascorrect ants {preproc_filename} {bias_filename} -bias bias.mif")
            os.system(f"mrview {bias_filename}")
            #mask
            mask_filename = f"dwi_den_eddy_bias_mask_{output_filename}.mif"
            os.system(f"dwi2mask {bias_filename} {mask_filename}")
            os.system(f"mrview {mask_filename}")
           



        if direction == "AP":
            ############################### PREPROCESAMIENTO ###########################################
            dwi_filename = f"dwi_{output_filename}.mif"
            os.system(f"mrconvert {input_filename} {dwi_filename} -fslgrad {bvec_filename} {bval_filename}")
            os.system(f"mrview {dwi_filename}")

            #denoise
            den_filename = f"dwi_den_{output_filename}.mif"
            os.system(f"dwidenoise {dwi_filename} {den_filename} -noise noise.mif")
            os.system(f"mrview {den_filename}")

            #Eddy current
            preproc_filename = f"dwi_den_eddy_{output_filename}.mif"
            os.system(f"dwifslpreproc {den_filename} {preproc_filename} -rpe_none -pe_dir AP -eddy_options \" --slm=linear \"")
            os.system(f"mrview {preproc_filename}")
            
            #bias
            bias_filename = f"dwi_den_eddy_bias_{output_filename}.mif"
            os.system(f"dwibiascorrect ants {preproc_filename} {bias_filename} -bias bias.mif")
            os.system(f"mrview {bias_filename}")
            
            #mask
            mask_filename = f"dwi_den_eddy_bias_mask_{output_filename}.mif"
            os.system(f"dwi2mask {bias_filename} {mask_filename}")
            os.system(f"mrview {mask_filename}")
           


            ################################### FODS #######################################################
            #obtener la función de respuesta de los tejidos
            os.system(f"dwi2response dhollander {bias_filename} wm.txt gm.txt csf.txt -fa 0.35 -gm 7 -sfwm 0.9 -csf 8 -voxels voxels.mif")
            #Observar la función de respuesta
            os.system(f"mrview {bias_filename} -overlay.load voxels.mif")
            os.system(f"shview wm.txt")
            os.system(f"shview gm.txt")
            os.system(f"shview csf.txt")
            #obtener la función de distribución de fibras
            os.system(f"dwi2fod msmt_csd {bias_filename} -mask {mask_filename} wm.txt wmfod.mif gm.txt gmfod.mif csf.txt csffod.mif -lmax 2,0,0")
            os.system(f"mrconvert -coord 3 0 wmfod.mif - | mrcat csffod.mif gmfod.mif - vf.mif")
            os.system(f"mtnormalise wmfod.mif wmfod_norm.mif gmfod.mif gmfod_norm.mif csffod.mif csffod_norm.mif -mask {mask_filename}")
            #observar la función de distribución de fibras
            os.system(f"mrview vf.mif -odf.load_sh wmfod_norm.mif")


            ############################ T1 #############################################
            # Conversion nifti2mif
            os.system(f"mrconvert {inputT1_filename} T1.mif")
            # Segmentación de la imagen anatomica utilizando fsl
            os.system(f"5ttgen fsl T1.mif 5tt_nocoreg.mif")
            #Extraer las imágenes b0
            os.system(f"dwiextract {bias_filename} - -bzero | mrmath - mean mean_b0.mif -axis 3")
            #Conversión a formato nifti
            os.system(f"mrconvert mean_b0.mif mean_b0.nii.gz")
            os.system(f"mrconvert 5tt_nocoreg.mif 5tt_nocoreg.nii.gz")
            #Extraer la segmentación de sustancia gris
            os.system(f"fslroi 5tt_nocoreg.nii.gz 5tt_vol0.nii.gz 0 1")
            #Corregistro de la imagen T1 con la imagen DTI
            os.system(f"flirt -in mean_b0.nii.gz -ref 5tt_vol0.nii.gz -interp nearestneighbour -dof 6 -omat diff2struct_fsl.mat")
            #Conversión de la matriz de corregistro
            os.system(f"transformconvert diff2struct_fsl.mat mean_b0.nii.gz 5tt_nocoreg.nii.gz flirt_import diff2struct_mrtrix.txt")
            # Command 8: Apply the transformation matrix to the non-coregistered segmentation data
            os.system(f"mrtransform 5tt_nocoreg.mif -linear diff2struct_mrtrix.txt -inverse 5tt_coreg.mif")
            # Command 9: View the coregistration in mrview
            os.system(f"mrview {bias_filename} -overlay.load 5tt_nocoreg.mif -overlay.colourmap 2 -overlay.load 5tt_coreg.mif -overlay.colourmap 1")
            # Command 10: Create the grey matter / white matter boundary
            os.system(f"5tt2gmwmi 5tt_coreg.mif gmwmSeed_coreg.mif")
            # Command 11: View the GM/WM boundary
            os.system(f"mrview {bias_filename} -overlay.load gmwmSeed_coreg.mif")

            ################################# TRACTOGRAFIA ###########################################
            #Obtener el archivo de los tractos, en este caso se calculan 1 millon 
            os.system(f"tckgen -act 5tt_coreg.mif -backtrack -seed_gmwmi gmwmSeed_coreg.mif -nthreads 8 -maxlength 250 -cutoff 0.06 -select {no_tracks} wmfod_norm.mif tracks_{no_tracks}.tck")
            #Ver la tractografía
            os.system(f"tckedit tracks_{no_tracks}.tck -number 200k tracks_200k.tck")
            os.system(f"mrview {bias_filename} -tractography.load tracks_200k.tck")
            #Obtener los mapas
            os.system(f"dwi2tensor {bias_filename} -mask {mask_filename} - | tensor2metric - -fa fa_map.mif -adc adc_map.mif -ad ad_map.mif -rd rd_map.mif")
            #observar los mapas
            os.system(f"mrview adc_map.mif")
            os.system(f"mrview fa_map.mif")
            os.system(f"mrview ad_map.mif")
            os.system(f"mrview rd_map.mif")

            ###################################### METRICAS ################################################

            #obtener las metricas en archivos de texto
            os.system(f"tcksample tracks_{no_tracks}.tck fa_map.mif fa_values.txt -stat_tck mean")
            os.system(f"tcksample tracks_{no_tracks}.tck adc_map.mif adc_values.txt -stat_tck mean")
            os.system(f"tcksample tracks_{no_tracks}.tck ad_map.mif ad_values.txt -stat_tck mean")
            os.system(f"tcksample tracks_{no_tracks}.tck rd_map.mif rd_values.txt -stat_tck mean")

            #Obtener el promedio de todas las metricas
            #ADC

            adc_mean = np.mean(np.loadtxt('adc_values.txt'))
            np.savetxt('adc_mean.txt', [adc_mean], fmt='%.18f')
            #FA
            fa_mean = np.mean(np.loadtxt('fa_values.txt'))
            np.savetxt('fa_mean.txt', [fa_mean], fmt='%.18f')
            #AD
            ad_mean = np.mean(np.loadtxt('ad_values.txt'))
            np.savetxt('ad_mean.txt', [ad_mean], fmt='%.18f')
            #RD
            rd_mean = np.mean(np.loadtxt('rd_values.txt'))
            np.savetxt('rd_mean.txt', [rd_mean], fmt='%.18f')
            #Imprimir valores
            print(f"DM: {adc_mean}, FA: {fa_mean}, AD: {ad_mean} RD: {rd_mean}")



    else:
        
        if direction == "AP-PA":
            for filename in os.listdir("."):
                #Conversion nifti2mif de la imagen AP
                if filename.endswith("AP_dwi.nii.gz"):
                    basename = os.path.splitext(filename)[0][:-3]
                    mif_filename = f"dwi_{output_filename}.mif"
                    os.system(f"mrconvert {filename} {mif_filename} -fslgrad {bvec_filename} {bval_filename}")
                   

                    #denoise
                    den_filename = f"dwi_den_{output_filename}.mif"
                    os.system(f"dwidenoise {mif_filename} {den_filename} -noise noise.mif")
                    meanap_filename = "mean_b0_AP.mif"
                    os.system(f"dwiextract {den_filename} - -bzero | mrmath - mean {meanap_filename} -axis 3")

                if filename.endswith("PA_dwi.nii.gz"):
                    basename = os.path.splitext(filename)[0][:-3]
                    bvecpa_filename = basename + "bvec"
                    bvalpa_filename = basename + "bval"
                    mifpa_filename = "PA.mif"
                    os.system(f"mrconvert {filename} {mifpa_filename}")
                    meanpa_filename = "mean_b0_PA.mif"
                    os.system(f"mrconvert {mifpa_filename} -fslgrad {bvecpa_filename} {bvalpa_filename} - | mrmath - mean {meanpa_filename} -axis 3")

            b0_filename = "b0_pair" + ".mif"
            os.system(f"mrcat {meanap_filename} {meanpa_filename} -axis 3 {b0_filename}")
            #Eddy current
            preproc_filename = f"dwi_den_eddy_{output_filename}.mif"
            os.system(f"dwifslpreproc {den_filename} {preproc_filename} -nocleanup -pe_dir AP -rpe_pair -se_epi {b0_filename} -eddy_options \" --slm=linear --data_is_shelled\"")
            #bias
            bias_filename = f"wi_den_eddy_bias_{output_filename}.mif"
            os.system(f"dwibiascorrect ants {preproc_filename} {bias_filename} -bias bias.mif")
            #mask
            mask_filename = f"wi_den_eddy_bias_mask_{output_filename}.mif"
            os.system(f"dwi2mask {bias_filename} {mask_filename}")
           

        if direction == "AP":
            ############################### PREPROCESAMIENTO ###########################################
            dwi_filename = f"dwi_{output_filename}.mif"
            os.system(f"mrconvert {input_filename} {dwi_filename} -fslgrad {bvec_filename} {bval_filename}")
            print('Etapa de preprocesamiento 0/4')

            #denoise
            den_filename = f"dwi_den_{output_filename}.mif"
            os.system(f"dwidenoise {dwi_filename} {den_filename} -noise noise.mif")
            print('Etapa de preprocesamiento 1/4')

            #Eddy current
            preproc_filename = f"dwi_den_eddy_{output_filename}.mif"
            os.system(f"dwifslpreproc {den_filename} {preproc_filename} -rpe_none -pe_dir AP -eddy_options \" --slm=linear \"")
            print('Etapa de preprocesamiento 2/4')

            #bias
            bias_filename = f"dwi_den_eddy_bias_{output_filename}.mif"
            os.system(f"dwibiascorrect ants {preproc_filename} {bias_filename} -bias bias.mif")
            print('Etapa de preprocesamiento 3/4')

            #mask
            mask_filename = f"dwi_den_eddy_bias_mask_{output_filename}.mif"
            os.system(f"dwi2mask {bias_filename} {mask_filename}")
            print('Etapa de preprocesamiento 4/4')
            print('Etapa de preprecesamiento terminada')


            ################################### FODS #######################################################
            #obtener la función de respuesta de los tejidos
            os.system(f"dwi2response dhollander {bias_filename} wm.txt gm.txt csf.txt -fa 0.35 -gm 7 -sfwm 0.9 -csf 8 -voxels voxels.mif")
            print('Estimación de la función de respuesta de los tejidos terminada')
            #obtener la función de distribución de fibras
            os.system(f"dwi2fod msmt_csd {bias_filename} -mask {mask_filename} wm.txt wmfod.mif gm.txt gmfod.mif csf.txt csffod.mif -lmax 2,0,0")
            os.system(f"mrconvert -coord 3 0 wmfod.mif - | mrcat csffod.mif gmfod.mif - vf.mif")
            os.system(f"mtnormalise wmfod.mif wmfod_norm.mif gmfod.mif gmfod_norm.mif csffod.mif csffod_norm.mif -mask {mask_filename}")
            print('Estimación de la función de orientación de fibras terminada')
           

            ############################ T1 #############################################
            # Conversion nifti2mif
            os.system(f"mrconvert {inputT1_filename} T1.mif")
            # Segmentación de la imagen anatomica utilizando fsl
            os.system(f"5ttgen fsl T1.mif 5tt_nocoreg.mif")
            #Extraer las imágenes b0
            os.system(f"dwiextract {bias_filename} - -bzero | mrmath - mean mean_b0.mif -axis 3")
            #Conversión a formato nifti
            os.system(f"mrconvert mean_b0.mif mean_b0.nii.gz")
            os.system(f"mrconvert 5tt_nocoreg.mif 5tt_nocoreg.nii.gz")
            #Extraer la segmentación de sustancia gris
            os.system(f"fslroi 5tt_nocoreg.nii.gz 5tt_vol0.nii.gz 0 1")
            #Corregistro de la imagen T1 con la imagen DTI
            os.system(f"flirt -in mean_b0.nii.gz -ref 5tt_vol0.nii.gz -interp nearestneighbour -dof 6 -omat diff2struct_fsl.mat")
            #Conversión de la matriz de corregistro
            os.system(f"transformconvert diff2struct_fsl.mat mean_b0.nii.gz 5tt_nocoreg.nii.gz flirt_import diff2struct_mrtrix.txt")
            # Command 8: Apply the transformation matrix to the non-coregistered segmentation data
            os.system(f"mrtransform 5tt_nocoreg.mif -linear diff2struct_mrtrix.txt -inverse 5tt_coreg.mif")
            # Command 10: Create the grey matter / white matter boundary
            os.system(f"5tt2gmwmi 5tt_coreg.mif gmwmSeed_coreg.mif")
            print('Corregistro de la imagen T1 con DTI terminado')
           


            ################################# TRACTOGRAFIA ###########################################
            #Obtener el archivo de los tractos, en este caso se calculan 1 millon 
            os.system(f"tckgen -act 5tt_coreg.mif -backtrack -seed_gmwmi gmwmSeed_coreg.mif -nthreads 8 -maxlength 250 -cutoff 0.06 -select {no_tracks} wmfod_norm.mif tracks_{no_tracks}.tck")
            print(f"Calculo de tractos terminada, se calcularon: {no_tracks} tractos")
            #Obtener los mapas
            os.system(f"dwi2tensor {bias_filename} -mask {mask_filename} - | tensor2metric - -fa fa_map.mif -adc adc_map.mif -ad ad_map.mif -rd rd_map.mif")
          

            ###################################### METRICAS ################################################

            #obtener las metricas en archivos de texto
            os.system(f"tcksample tracks_{no_tracks}.tck fa_map.mif fa_values.txt -stat_tck mean")
            os.system(f"tcksample tracks_{no_tracks}.tck adc_map.mif adc_values.txt -stat_tck mean")
            os.system(f"tcksample tracks_{no_tracks}.tck ad_map.mif ad_values.txt -stat_tck mean")
            os.system(f"tcksample tracks_{no_tracks}.tck rd_map.mif rd_values.txt -stat_tck mean")
          

            #Obtener el promedio de todas las metricas
            #ADC

            adc_mean = np.mean(np.loadtxt('adc_values.txt'))
            np.savetxt('adc_mean.txt', [adc_mean], fmt='%.18f')
            #FA
            fa_mean = np.mean(np.loadtxt('fa_values.txt'))
            np.savetxt('fa_mean.txt', [fa_mean], fmt='%.18f')
            #AD
            ad_mean = np.mean(np.loadtxt('ad_values.txt'))
            np.savetxt('ad_mean.txt', [ad_mean], fmt='%.18f')
            #RD
            rd_mean = np.mean(np.loadtxt('rd_values.txt'))
            np.savetxt('rd_mean.txt', [rd_mean], fmt='%.18f')
            #Imprimir valores
            print(f"DM: {adc_mean}, FA: {fa_mean}, AD: {ad_mean} RD: {rd_mean}")





if __name__ == '__main__':
    if len(sys.argv) < 8:
        print('Advertencia: Argumentos incompletos \n' 
              'Argumentos de entrada:')

    if len(sys.argv) <8 and sys.argv[1] == '-help':
        print('Función para la extracción de métricas de difusividad global de una imagen DTI \n'
              'Uso de la función: python DWImetrics.py [input] [output] [bvec] [bval] [Direction] [T1 image] [Tracks] [view]\n'
              'Argumentos de entrada: \n -input: Imagen DTI en formato NIfTI \n -output: Nombre del archivo de salida \n -bvec: Nombre del archivo bvec \n'
              ' -bval: Nombre del archivo bval \n -Direction: Fase de codificación AP o AP-PA \n -T1: Imagen T1 en formato NIfTI \n -Tracks: Número de tractos que se' 
              'desean calcular en la tractpgrafía \n -view: Opción para visualizar el avance de la ejecución, si se desea activar la \n'
              ' visuzalición seleccionar se debe escribir "True" en caso contrario \n' 
               ' no se debe de escribir nada, ya que por default view=False \n'
               'Salidas de la función: \n'
               '-DM: Difusividad media \n'
               '-FA: Anisotropía fraccional \n'
               '-AD: Difusividad radial \n'
               '-RD: Difusividad radial')  

    else:
        try:
        
            input_filename = sys.argv[1]
            output_filename = sys.argv[2]
            bvec_filename = sys.argv[3]
            bval_filename = sys.argv[4]
            direction = sys.argv[5]
            inputT1_filename = sys.argv[6]
            no_tracks = sys.argv[7]
                
            if len(sys.argv) == 9:
                
            #PONER UNA CONDICION EN CASO DE QUE SE QUIERA USAR VIEW PERO HAGA FALTA UN ARGUMENTO POR QUE TECNICAMENTE SI SON 8 ENTONCES NO APLICA EL PRIMER IF 
                view = sys.argv[8]
           
            DTImetrics(input_filename, output_filename, bvec_filename, bval_filename, direction, inputT1_filename, no_tracks, view)

        except IndexError:
            print('python DWImetrics.py [input] [output] [bvec] [bval] [Direction] [T1 image] [Tracks] [view]')
            

    

                                                                                              






