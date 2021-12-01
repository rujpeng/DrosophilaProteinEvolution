"""

    The script is to get alternative CDS from VCF. 

    The Dmel VCF file is downloaded from dgrp2.gnets.ncsu.edu/data.html, 
    containing genotypes of 205 Dmel individuals

    The Dsim VCF file is downloaded from zenodo.org/record/154261#.XY0Q-MDPxUQ 
    containing genotypes of 195 Dsim individuals

    The script generates 2*individuals alternative genomes excluding indels.

    Created by jpeng; 09/11/2019

"""

import sys,copy,subprocess,gzip
import numpy as np
from multiprocessing import Pool
from fasta2seq import *
#from tqdm import tqdm


## watson crick base pairs ##
WCBP = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}

def update(pbar,*a):
    pbar.update()

def readlines(f):
    try:
        #with open(f,'r') as p:
        #    lines = p.readlines()
        if f[-2:] == 'gz':
            lines  = gzip.open(f,'rt')
        else:
            lines  = open(f,'r')
        nlines = int(subprocess.check_output("wc -l %s"%f,shell=True).split()[0])
    except IOError:
        print("cannot read file %s"%f)
        sys.exit(0)
    return lines,nlines

class CoorMap():
    """
        Class objects for single site v5-v6 mapping
        - self.coor:    store V5 coordinates of the mapping, e,g. "2L:1989"
        - self.chrom:   store the chromosome information
        - self.pos:     store the V6 sites on the self.chrom chromosome.
    """
    def __init__(self,coor_str,cds_id):
        coor  = coor_str.split(':')
        chrom = coor[0]
        pos   = coor[1]
        self.pos   = pos
        self.coor  = coor_str
        self.chrom = chrom
        self.cds_ids = [cds_id]

    def update(self,cds_id):
        self.cds_ids.append(cds_id)

class SNP():
    """
        Class objects for single site SNP
        - self.chrom: store which chromosome the SNP site locates on.
        - self.v6pos: store the specific site of the SNP on self.chrom.
        - self.variants: store all the genotype information of the SNP site.
    """
    def __init__(self,coormap,variants):
        self.chrom    = coormap.chrom
        self.pos      = coormap.pos
        self.variants = variants

class VCFReader():
    """
        Class objects for all sites v5-v6 mapping and genotypes
        - self.coormap: all the SNP sites v5-v6 mapping: {'V5coor':Map, ...}
        - self.snp_coordinates: all the SNP sites v6coor
        - self.snp_variants: all the SNP sites genotype (the keys are v6coor)
    """

    def __init__(self):
        self.snp_coordinates = [] # to store coor of all SNP sites
        self.snp_variants    = {} # to store v6-variants mapping

    def add_coor(self,coor_str):
        self.coormap[coor_str] = CoorMap(coor_str)

    def add_variants(self,coormap,variants):
        coor = coormap.coor
        snp  = SNP(coormap,variants)
        self.snp_variants[coor] = snp

    def variantsMoreThan5percent(self,snps,ref_nt,var_nt,delimiter):
        """ Returns variants if we find more than 5% of all allels have SNPs.
            In Dmel case, if a site has less than (5%*410=) 20 SNPs, this SNP 
            is disregarded in future analysis.

            delimiter can be '/' or '|'
        """
        ntot = 0
        nvar = 0
        variants = []
        for snpi in snps:
            #vari = snpi.split('/')
            vari = snpi.split(delimiter)
            i = 0 if vari[0]=='0' else 1
            j = 0 if vari[1]=='0' else 1
            a0 = var_nt if vari[0]=='1' else ref_nt
            a1 = var_nt if vari[1]=='1' else ref_nt
            ntot += 2
            nvar += i+j
            variants += [a0,a1]
        #if nvar/ntot >= 0.05:
        #    return variants
        #elif nvar/ntot <  0.05:
        #    return False
        return variants

    def process_vcf_line(self,line,delimiter,coormap):
        """specify delimiter that seperate the genotype ('/' or '|')
        """
        if not line.startswith("#"): 
            info  = line.split()
            chrom = info[0]  ## add 'chr' befor each chrom
            pos   = info[1]
            ref_nt= info[3]
            var_nt= info[4]
            snps  = info[9:]


            coor = "%s:%s"%(chrom,pos)
            if coor in coormap:
                if len(ref_nt)==1 and len(var_nt)==1:
                    ## to determin if a SNP is significant ##
                    #print(line)
                    variants = self.variantsMoreThan5percent(snps,ref_nt,
                                                            var_nt,delimiter)
                    if variants:
                        cmap = coormap[coor]
                        self.snp_coordinates += [coor]
                        self.add_variants(cmap,variants)
                        #print(">Warn! Unmapped key: %s"%coor5)
        else:
            pass
         

    def read_vcf(self,fvcf,coormap,delimiter='/'):
        """ - Reads in a VCF with version coordinates by default. 
            - Please specify delimiter that seperate the genotype ('/' or '|')
            - Reutrns:
              - the list of 'coor', self.snp_coordinates
              - the dictionary self.snp_variants: {'coor': [variants], ...}
        """
        print('Opening %s to read'%fvcf)
        lines,nlines = readlines(fvcf)
        print('%s opened'%fvcf)
        #plines  = tqdm(lines,ascii=True,unit='B', unit_scale=True, unit_divisor=1024)
        #plines  = tqdm(lines,ascii=True, unit_scale=True, unit_divisor=1000)
        #plines.set_description("ReadVCF")
        #for line in plines:
        freq = max(10**(int(np.log(nlines)/np.log(10))-3),1)
        i_now = 0
        for line in lines:
            self.process_vcf_line(line,delimiter,coormap)
            if i_now==0 or i_now%freq==0 or i_now==nlines-1:
                percent = (i_now/(nlines))*100
                sys.stdout.write("\rReadVCF... %5.2f%%\r" % percent)
            i_now += 1
        sys.stdout.write('\nFinished VCF file\n')
        #print('Processing vcf')
        #pool = Pool(ncpu)
        #pool.starmap(self.process_map_line,lines)
        #pool.close()
        #poo/l.join()
        #print('Finished vcf')


    def update(self,fvcf,coormap,delimiter='/'):
        """ If vcf uses V5 coordinates and Genome is V6 coordinates
            Please specify delimiter that seperate the genotype ('/' or '|')
        """
        self.read_vcf(fvcf,coormap,delimiter=delimiter)

class GenomeReader():

    def __init__(self):
        self.coormap = dict()

    def read_genome(self,fasta):
        """ Read the genome file
            To save time & memory, it's better to remove line breaks of 
            the genome fasta file. 
            *One line per chromosome*
             >2L
             ATCGATCG....//....ATCGATCG
             >X
             ATCGATCG....//....ATCGATCG
        """
        print('Opening %s to read'%fasta)
        self.sequences = fasta2seq(fasta,progress_bar='on')
        print('Finished reading %s'%fasta)

    def get_snp(self,fvcf,delimiter="/"):
        """ Read the genome file
            Get SNP information from vcf file.
            - initialize self.alternative_genome
            - initialize self.snp_coordinates from vcf.snp_coordinates
            - initialize self.snp_variants from vcf.snp_variants
            - Returns:
              - self.snp_num: total number of SNPs (excluding indels)
              - self.npopulations: total number of alter genomes (410 for Dmel)
        """

        ## coormap is used to refine search region in VCF ##
        ## first split each cds coordinates to dict ##
        ## this will enable fast indexing like hash ##

        coormap = dict()

        sys.stdout.write('CDS to dict for fast indexing...\n')
        nlines = len(self.sequences)
        i_now  = 0
        freq   = 100
        for cds_id in self.sequences:
            for coor_str in cds_id.split(";"):
                chrom,start,end = coor_str.split(":")
                if "-" in chrom:
                    strand = chrom[-1]
                    chrom  = chrom[0:-1]
                else:
                    strand = "+"
                start  = int(start)
                end    = int(end)
                for i in range(start,end+1):
                    new_str = "%s:%s"%(chrom,i)
                    if new_str not in coormap:
                        coormap[new_str] = CoorMap(new_str,cds_id)
                    else:
                        coormap[new_str].update(cds_id)

            i_now += 1
            if i_now==0 or i_now%freq==0 or i_now==nlines-1:
                percent = (i_now/nlines)*100
                sys.stdout.write("\rCDS to dict... %5.2f%%\r" % percent)


        vcf = VCFReader()
        vcf.update(fvcf,coormap,delimiter=delimiter)

        self.snp_coordinates = vcf.snp_coordinates
        self.snp_variants    = vcf.snp_variants
        #self.snp_num = len(self.snp_coordinates)

        ## populations ##
        #print(vcf.snp_coordinates)
        if self.snp_coordinates:
            coor0 = self.snp_coordinates[0]
            npopulations = len(vcf.snp_variants[coor0].variants)
            print("Total number of populations (haplotypes)", npopulations)
        else:
            npopulations = 0
            print("No SNPs read, exit program")
            sys.exit(0)
    
        self.npopulations = npopulations


        ### now assign SNPS to each CDS ###

        ## then assign snps to each CDS ##
        sys.stdout.write('Assign SNPs to CDS...\n')
        snp_in_cds = dict()
        nlines     = len(self.snp_variants)
        i_now      = 0
        freq       = 100
        for coor_str in self.snp_variants:
            chrom,pos = coor_str.split(':')
            pos       = int(pos)
            cds_ids   = coormap[coor_str].cds_ids
            var       = self.snp_variants[coor_str]
            for cds_id in cds_ids:
                if cds_id in snp_in_cds:
                    snp_in_cds[cds_id].append([pos,var])
                else:
                    snp_in_cds[cds_id] = [[pos,var]]

            if i_now==0 or i_now%freq==0 or i_now==nlines-1:
                percent = (i_now/(nlines))*100
                sys.stdout.write("\rAssign SNPs to CDS... %5.2f%%\r" % percent)
            i_now += 1
        sys.stdout.write("Assigned SNPs to CDS... %5.2f%%\n" % percent)
        self.snp_in_cds = snp_in_cds
        #print(len(self.snp_in_cds))

    def mutate_one(self,cds_key,ikey,outdir,species):
        """ Mutate cds sequence
        """

        ## extract snps in this CDS ##
        snps = self.snp_in_cds[cds_key]

        ## mutate and write this alternative genome ##
        coor_strs  = cds_key.split(';')
        coor_range = []
        strand     = ''
        for coor_str in coor_strs:
            chrom,start,end = coor_str.split(':')
            if '-' in chrom:
                strand = chrom[-1]
                chrom  = chrom[0:-1]
            else:
                strand = '+'
            start,end  = [int(s) for s in [start,end]]
            coor_range.append([start,end])

        if strand == '-':
            coor_range = coor_range[::-1]
        elif strand == '+':
            pass
        else:
            sys.stdout.write("strand \'%s\' not recognized!\n")

        ## obtain zero based index of each snp in CDS ##
        snp_index = []
        snp_vars  = []
        for snp in snps:
            ## each snp contain the position and variant GenoType ##
            pos,var = snp
            chrom   = var.chrom
            var     = var.variants
            idx     = 0
            index   = 0
            snp_vars.append(var)

            for crange in coor_range:
                if pos>=crange[0] and pos<=crange[1]:
                    if strand == '+':
                        index += pos-crange[0]
                    else:
                        index += crange[1]-pos
                    break
                else:
                    index += crange[1]-crange[0] + 1
                    idx += 1
            snp_index.append(index)
           #if cds_key == "chr13-:28877307-28877505;chr13-:28880815-28880909;chr13-:28882980-28883064;chr13-:28885727-28885869;chr13-:28886130-28886235;chr13-:28891635-28891734;chr13-:28893560-28893671;chr13-:28895600-28895722;chr13-:28896399-28896496;chr13-:28896927-28897083;chr13-:28901599-28901687;chr13-:28903752-28903865;chr13-:28908162-28908266;chr13-:28913305-28913437;chr13-:28919582-28919688;chr13-:28931691-28931822;chr13-:28959022-28959168;chr13-:28963933-28964241;chr13-:28971097-28971205;chr13-:28979917-28980031;chr13-:29001296-29001455;chr13-:29001889-29002058;chr13-:29004187-29004304;chr13-:29005273-29005447;chr13-:29007956-29008092;chr13-:29008195-29008357;chr13-:29012358-29012482;chr13-:29041040-29041266;chr13-:29041658-29041754;chr13-:29068917-29068980":
           #    uniq_var = dict()
           #    for v in var:
           #        if v in uniq_var:
           #            uniq_var[v] += 1
           #        else:
           #            uniq_var[v] = 1
         
           #    print(chrom,pos,strand,index,uniq_var,coor_range)

        ## now mutate and write ##
        fasta = '%s/msa_%d.fasta'%(outdir,ikey)
        f     = open(fasta,'w')
        f.write('>%s_0\n%s\n'%(species,self.sequences[cds_key]))

        ## initialize the alternative cds ##
        original_cds = self.sequences[cds_key]
        for i in range(self.npopulations):
            alternative_cds = [s for s in original_cds]
            for index,snp_var in zip(snp_index,snp_vars):
                var = snp_var[i]
                if strand == '-':
                    var = WCBP[var]
                alternative_cds[index] = var

            f.write('>%s_%d\n%s\n'%(species,i+1,''.join(alternative_cds)))

        print('Finished mutating CDS for %s %d'%(cds_key,ikey))

    def mutate(self,outdir,ncpu = 1, species="hg19"):
        """ Final main() 
            Note that the multiprocessing is not optimized, 
            it may not save time
        """
        if ncpu==1:
            ikey = 0
            ## only mutate CDS that have SNPs ##
            for cds_key in self.snp_in_cds:
                self.mutate_one(cds_key,ikey,outdir,species)
                ikey += 1

        elif ncpu > 1:
            #for ialt in range(10):
            pool = Pool(ncpu)
            ikey = 0
            ## only mutate CDS that have SNPs ##
            for cds_key in self.snp_in_cds:
                pool.apply_async(self.mutate_one,
                                args=(cds_key,ikey,outdir,species,))
                ikey += 1
            pool.close()
            pool.join()

if __name__ == '__main__':

    if len(sys.argv)==5:
        vcf    = sys.argv[1]
        fasta  = sys.argv[2]
        outdir = sys.argv[3]
        name   = sys.argv[4]
       
    else:
        print("Usage: python vcf2msa.py <vcf> <fasta> <outdir> <species_name>")
        sys.exit(0)

    genome = GenomeReader()
    genome.read_genome(fasta)

    genome.get_snp(vcf,delimiter="|")
    genome.mutate(outdir,ncpu=1,species=name)
