#!/usr/bin/env Rscript
# We'll use lattice for plotting
suppressPackageStartupMessages(library(lattice))

# Read in data
results <- read.csv('results.csv', as.is=TRUE)

# Find the median of elapsed time
agg_time <- aggregate(elapsed~algorithm+k, median, data=results)

# And the median max memory use
agg_memory <- aggregate(maxmem~algorithm+k, median, data=results)


# Plot the median elapsed time, and median memory use
key <- list(x=0, y=.8, corner=c(0, 0), pch=22)
timeplot <- xyplot(elapsed~k,data=agg_time, groups=algorithm, auto.key=key,
                   ylab="Median elapsed time (s)", main="Runtime")
memplot <- xyplot(maxmem~k,data=agg_memory, groups=algorithm, auto.key=key,
                  ylab="Median memory use", main='Memory use')

png('plots.png')
print(timeplot, split=c(1,1,1,2), more=TRUE)
print(memplot, split=c(1,2,1,2))
dev.off()
