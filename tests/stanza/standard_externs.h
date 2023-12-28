#ifndef __STD_EXTERNS_H__
#define __STD_EXTERNS_H__


extern int func_no_args(void);
extern int func_one_arg_int(int a);
extern int func_one_arg_double(double a);
extern int func_one_arg_float(float a);
extern int func_one_arg_long(long a);
extern int func_one_arg_char(char a);
extern int func_one_arg_char_p(char *a);
extern int func_one_arg_cchar_p(const char *a);

/* Type Modifiers */
extern long int func_one_arg_long_mod_ret(int a);
extern int func_one_long_mod_arg(long int a);

extern short int func_one_arg_short_mod_ret(int a);
extern int func_one_short_mod_arg(short int a);


/* Helpers for extracting the values from the functions
   that return void. */
extern void reset_cached_val();
extern int get_cached_val();

extern void func_no_args_void(void);
extern void func_one_arg_int_void(int a);
extern void func_one_arg_double_void(double a);
extern void func_one_arg_float_void(float a);
extern void func_one_arg_long_void(long a);
extern void func_one_arg_char_void(char a);
extern void func_one_arg_char_p_void(char *a);
extern void func_one_arg_cchar_p_void(const char *a);

/* Multi-Argument Signature */
extern long func_multi_arg_0(int a, unsigned int b, float c);
extern float func_multi_arg_1(unsigned long a, float b, char c);
extern double func_multi_arg_2(double a, double b, double *c);
extern double func_multi_arg_3(double **a, double **b, double **c, unsigned long cnt);

extern int func_no_arg_names(int, long);
extern void *func_with_void_ptr_ret(long);


/*
 Working with Structs
 Bug in python code - need to fix before these will run and work
 */

struct test1 {
  int a;
  int b;
};

extern int test1_init_struct(struct test1 *obj);
extern int test1_add(struct test1 *obj, int a);
extern struct test1 *test1_copy(struct test1 *obj);
extern int test1_compare(struct test1 *obj1, struct test1 *obj2);


/* Function Pointer Tests
*/

typedef void (*SignalHandler)(long signum);

/* TODO - `long int` is not getting treated as `long` - gets converted to int*/
extern SignalHandler get_handler(long signum);
extern SignalHandler set_handler(long signum, SignalHandler handler);

/* Implicit (Anonymous) Function Pointers */
extern long set_handler_implicit(long signum, void (*)(long));

#endif