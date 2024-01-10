#include "standard_externs.h"

int func_no_args() {
  return 42;
}

int func_one_arg_int(int a) {
  return a * 3;
}

int func_one_arg_double(double a) {
  return ( (int)a ) * 4 ;
}

int func_one_arg_float(float a) {
  return ( (int)a ) * 5 ;
}

int func_one_arg_long(long a) {
  return ( (int)a ) * 6 ;
}

int func_one_arg_char(char a) {
  return ( (int)a ) * 7 ;
}

int func_one_arg_char_p(char *a) {
  int ret = 0;
  int i = 0;
  while(1) {
    if (a[i] == 0) {
      break;
    }
    ret += (int)a[i];
    i++;
  }
  return ret * 2;
}

int func_one_arg_cchar_p(const char *a) {
  int ret = 0;
  int i = 0;
  while(1) {
    if (a[i] == 0) {
      break;
    }
    ret += (int)a[i];
    i++;
  }
  return ret * 3;
}

long int func_one_arg_long_mod_ret(int a) {
  return (long)(a * 61);
}

int func_one_long_mod_arg(long int a) {
  return (int)(a * 2);
}

short int func_one_arg_short_mod_ret(int a) {
  return (short)(a * 3);
}

int func_one_short_mod_arg(short int a) {
  return (int)(a * 5);
}

static int _LOCAL = -1;

void reset_cached_val() {
  _LOCAL = -1;
}

int get_cached_val() {
  return _LOCAL;
}

// Functions with Void Return

void func_no_args_void(void) {
  _LOCAL = -13;
}

void func_one_arg_int_void(int a) {
  _LOCAL = func_one_arg_int(a);
}

void func_one_arg_double_void(double a) {
  _LOCAL = func_one_arg_double(a);
}

void func_one_arg_float_void(float a) {
  _LOCAL = func_one_arg_float(a);
}

void func_one_arg_long_void(long a) {
  _LOCAL = func_one_arg_long(a);
}

void func_one_arg_char_void(char a) {
  _LOCAL = func_one_arg_char(a);
}

void func_one_arg_char_p_void(char* a) {
  _LOCAL = func_one_arg_char_p(a);
}

void func_one_arg_cchar_p_void(const char* a) {
  _LOCAL = func_one_arg_cchar_p(a);
}

/* Multiple Args */

long func_multi_arg_0(int a, unsigned int b, float c) {
  return (long)a * ((long)b) * ((long)c);
}

float func_multi_arg_1(unsigned long a, float b, char c) {
  return (float)a * b * ((float)c);
}

double func_multi_arg_2(double a, double b, double *c) {
  if (c != 0) {
    return *c + a + b;
  } else {
    return -1.0;
  }
}

double func_multi_arg_3(double **a, double **b, double **c, unsigned long cnt) {
  double ret = 0.0;

  for ( int i = 0; i < cnt; i++ ) {
    ret += a[0][i] + b[0][i] + c[0][i];
  }
  return ret;
}


/*  Function with off-signatures */

int func_no_arg_names(int a, long b) {
  return a * 43 + (int)b;
}

void *func_with_void_ptr_ret(long a) {
  return (void *)(a * 3);
}

/** Basic Structs */

int test1_init_struct(struct test1 *obj) {
  return (obj->a + obj->b );
}

int test1_add(struct test1 *obj, int a) {
  obj->a += a;
  return 2 * (obj->a + obj->b);
}

struct test1 *test1_copy(struct test1 *obj) {
  return obj;
}

int test1_compare(struct test1 *obj1, struct test1 *obj2) {
  if ( obj1->a > obj2->a ) {
    return 1;
  } else {
    return -1;
  }
}

int test2_init_struct(test2 *obj) {
  return (int)(obj->a + obj->b );

}

int test2_add(test2 *obj, unsigned long int a) {
  return (int) ((obj->a * obj->b) + (long)a);
}

test2 *test2_copy(test2 *obj) {
  return obj;
}

int test2_compare(test2 *obj1, test2 *obj2) {
  if (obj1->a < obj2->a) {
    return 10;
  } else {
    return -10;
  }
}



/* Function Pointer - Basics*/

SignalHandler get_handler(long signum) {
  return (SignalHandler)(signum + 3L);
}

SignalHandler set_handler(long signum, SignalHandler handler) {
  return (SignalHandler)(signum * 3L  + (long)handler);
}

long set_handler_implicit(long signum, void (*h)(long)) {
  return (signum * 7L) + (long)h;
}

long set_z3_error_handler(Z3_error_handler h) {
  return 10L + (long)h;
}
