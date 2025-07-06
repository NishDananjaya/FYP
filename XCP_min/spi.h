/*
 * spi.h
 *
 *  Created on: May 21, 2025
 *      Author: pathu
 */

#ifndef SPI_H
#define SPI_H

#include "stm32f1xx_hal.h"

#define SPI_BUFFER_SIZE 8

extern SPI_HandleTypeDef hspi1;
extern DMA_HandleTypeDef hdma_spi1_rx;
extern DMA_HandleTypeDef hdma_spi1_tx;

void SPI_Init(void);
void SPI_Start(void);

#endif
