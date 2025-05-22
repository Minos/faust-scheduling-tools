pfm_info: pfm_info.c
	$(CC) -lpfm $< -o $@

clean:
	@rm -f pfm_info
